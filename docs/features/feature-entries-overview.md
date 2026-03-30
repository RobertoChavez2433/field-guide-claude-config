---
feature: entries
type: overview
scope: Daily Job Site Entry Management
updated: 2026-03-30
---

# Entries Feature Overview

## Purpose

The Entries feature enables construction inspectors to create and manage daily job site reports. Each entry captures weather conditions, site activities, safety measures, personnel, equipment, contractors, and attached photos. Entries support offline creation, draft-to-complete workflow, and signature-based submission for compliance and documentation.

## Key Responsibilities

- **Daily Entry Creation**: Capture date, weather, temperature, activities, and safety information for each job site visit
- **Site Documentation**: Record personnel, equipment, contractors involved in daily work
- **Photo Attachment**: Link photos captured on-site to specific entries
- **Form Attachment**: Link completed toolbox forms to entries
- **Quantity Tracking**: Reference extracted bid items and track quantities completed
- **Entry Status Management**: Draft → Complete → Submitted lifecycle with signature support
- **Entry Aggregation**: Display entries as calendar view or list for project review
- **Data Validation**: Ensure required fields (location, weather, activities) are complete before submission
- **Export**: Generate exportable snapshots of entry data for PDF generation

## Key Files

### Use Cases

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/entries/domain/usecases/load_entries_use_case.dart` | `LoadEntriesUseCase` | Fetch entries for a project with pagination |
| `lib/features/entries/domain/usecases/manage_entry_use_case.dart` | `ManageEntryUseCase` | Create, update, and delete entries |
| `lib/features/entries/domain/usecases/submit_entry_use_case.dart` | `SubmitEntryUseCase` | Transition entry to submitted status |
| `lib/features/entries/domain/usecases/undo_submit_entry_use_case.dart` | `UndoSubmitEntryUseCase` | Reverse a submission transition |
| `lib/features/entries/domain/usecases/batch_submit_entries_use_case.dart` | `BatchSubmitEntriesUseCase` | Submit multiple entries at once |
| `lib/features/entries/domain/usecases/calendar_entries_use_case.dart` | `CalendarEntriesUseCase` | Load entries grouped by date for calendar display |
| `lib/features/entries/domain/usecases/filter_entries_use_case.dart` | `FilterEntriesUseCase` | Filter entry list by status, date range, or keyword |
| `lib/features/entries/domain/usecases/export_entry_use_case.dart` | `ExportEntryUseCase` | Build exportable entry snapshot for PDF/share |

### Controllers

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/entries/presentation/controllers/entry_editing_controller.dart` | `EntryEditingController` | Text field and form editing state |
| `lib/features/entries/presentation/controllers/contractor_editing_controller.dart` | `ContractorEditingController` | Contractor and personnel editing state |
| `lib/features/entries/presentation/controllers/photo_attachment_manager.dart` | `PhotoAttachmentManager` | Photo attachment lifecycle state |
| `lib/features/entries/presentation/controllers/form_attachment_manager.dart` | `FormAttachmentManager` | Form attachment lifecycle state |
| `lib/features/entries/presentation/controllers/pdf_data_builder.dart` | `PdfDataBuilder` | Assembles entry data structure for PDF generation |

### Providers

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/entries/presentation/providers/daily_entry_provider.dart` | `DailyEntryProvider` | Entry list state management, extends `BaseListProvider` |
| `lib/features/entries/presentation/providers/entry_export_provider.dart` | `EntryExportProvider` | Export state management |
| `lib/features/entries/presentation/providers/calendar_format_provider.dart` | `CalendarFormatProvider` | Calendar view format preference state |

### Screens

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/entries/presentation/screens/home_screen.dart` | `HomeScreen` | Calendar view and entry list for a project |
| `lib/features/entries/presentation/screens/entry_editor_screen.dart` | `EntryEditorScreen` | Unified entry creation and editing |
| `lib/features/entries/presentation/screens/entry_review_screen.dart` | `EntryReviewScreen` | Read-only review of a completed entry |
| `lib/features/entries/presentation/screens/review_summary_screen.dart` | `ReviewSummaryScreen` | Summary view before final submission |
| `lib/features/entries/presentation/screens/entries_list_screen.dart` | `EntriesListScreen` | Flat list of all entries for a project |
| `lib/features/entries/presentation/screens/drafts_list_screen.dart` | `DraftsListScreen` | List of draft (incomplete) entries |

### Report Widgets Sub-directory

`lib/features/entries/presentation/screens/report_widgets/` — Modular dialogs and sheets used inside the editor and review screens (weather edit, location edit, add contractor, add quantity, photo detail, PDF actions, etc.).

### Models

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/entries/data/models/daily_entry.dart` | `DailyEntry` | Core entry model with weather, activities, signature fields |
| `lib/features/entries/data/models/document.dart` | `Document` | Attached document/form reference model |
| `lib/features/entries/data/models/entry_export.dart` | `EntryExport` | Serializable snapshot for export/PDF |

### Repositories

| File Path | Purpose |
|-----------|---------|
| `lib/features/entries/data/repositories/daily_entry_repository.dart` | CRUD for entries (implements domain interface) |
| `lib/features/entries/data/repositories/document_repository.dart` | CRUD for attached documents |
| `lib/features/entries/data/repositories/entry_export_repository.dart` | Persists and retrieves export snapshots |

## Data Sources

- **SQLite**: Persists daily entries, contractors, personnel, equipment, quantities, and documents locally
- **Photos**: Links to photos stored in `photos` feature
- **Bid Items**: References extracted bid items from `quantities` feature
- **Contractors**: Links to contractor and equipment data from `contractors` feature
- **Weather Data**: Integration with `weather` feature for auto-populated conditions
- **Forms**: Links completed form responses from `forms` feature

## Integration Points

**Depends on:**
- `core/database` — SQLite schema for entries and related entities
- `projects` — Project context for entries
- `contractors` — Contractor, equipment, and personnel type data
- `quantities` — Bid items for quantity tracking
- `locations` — Project locations for entry references
- `photos` — Photo storage and retrieval
- `weather` — Auto-populate weather conditions
- `forms` — Form responses attached to entries

**Required by:**
- `sync` — Entry data synced to Supabase after completion
- `pdf` — `PdfDataBuilder` assembles entry data consumed by PDF generation

## Offline Behavior

Entries are **fully offline-capable**. Inspectors can create, edit, and complete entries without network connectivity. All data is stored locally until sync operations occur. Entry creation is immediate; changes persist in SQLite. Sync is deferred until connectivity available (handled by `sync` feature).

## Edge Cases & Limitations

- **Signature Capture**: Requires biometric signature or tap-based signature widget; no digital PKI verification
- **Photo References**: Entries can reference existing photos; new photos must be created via `photos` feature
- **Contractor Assignment**: Contractors must be pre-created in project setup before assignment to entry
- **Multi-Location Support**: Entries reference single location per date; multi-location work requires separate entries
- **Status Immutability**: Entry status transitions are one-way (Draft → Complete → Submitted); `UndoSubmitEntryUseCase` provides a controlled reversal path
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
