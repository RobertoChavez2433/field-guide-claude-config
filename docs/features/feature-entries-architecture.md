---
feature: entries
type: architecture
scope: Daily Job Site Entry Management
updated: 2026-03-30
---

# Entries Feature Architecture

## Overview

The entries feature manages daily job-site reports (DailyEntry records). It is the most
complex feature in the app, with a full clean-architecture stack: domain interfaces, use
cases, concrete data implementations, presentation providers, and a controller-based editor
pattern. Offline-first — all writes go to SQLite; the sync feature handles cloud push.

## File Tree

```
lib/features/entries/
├── di/
│   └── entries_providers.dart          # Tier-4 DI wiring
├── domain/
│   ├── repositories/
│   │   ├── daily_entry_repository.dart  # Abstract interface
│   │   ├── entry_export_repository.dart # Abstract interface
│   │   ├── document_repository.dart     # Abstract interface
│   │   └── repositories.dart            # Barrel
│   └── usecases/
│       ├── submit_entry_use_case.dart
│       ├── undo_submit_entry_use_case.dart
│       ├── batch_submit_entries_use_case.dart
│       ├── export_entry_use_case.dart
│       ├── filter_entries_use_case.dart
│       ├── load_entries_use_case.dart
│       ├── manage_entry_use_case.dart
│       ├── calendar_entries_use_case.dart
│       └── usecases.dart               # Barrel
├── data/
│   ├── models/
│   │   ├── daily_entry.dart            # Core entry model (barrel-exported)
│   │   ├── entry_export.dart           # Export snapshot model (not in barrel)
│   │   └── document.dart               # Document attachment model (not in barrel)
│   ├── datasources/
│   │   ├── local/
│   │   │   ├── daily_entry_local_datasource.dart  (barrel-exported)
│   │   │   ├── entry_export_local_datasource.dart (not in barrel)
│   │   │   └── document_local_datasource.dart     (not in barrel)
│   │   └── remote/
│   │       ├── daily_entry_remote_datasource.dart (barrel-exported)
│   │       ├── document_remote_datasource.dart    (not in barrel)
│   │       └── entry_export_remote_datasource.dart (not in barrel)
│   └── repositories/
│       ├── daily_entry_repository.dart   # DailyEntryRepositoryImpl
│       ├── entry_export_repository.dart  # EntryExportRepositoryImpl
│       ├── document_repository.dart      # DocumentRepositoryImpl
│       └── repositories.dart             # Barrel
├── presentation/
│   ├── models/
│   │   ├── contractor_ui_state.dart     # ContractorUiState presentation model
│   │   └── models.dart                  # Barrel
│   ├── providers/
│   │   ├── daily_entry_provider.dart    # DailyEntryProvider
│   │   ├── entry_export_provider.dart   # EntryExportProvider
│   │   ├── calendar_format_provider.dart # CalendarFormatProvider
│   │   └── providers.dart               # Barrel
│   ├── controllers/
│   │   ├── entry_editing_controller.dart    # EntryEditingController
│   │   ├── contractor_editing_controller.dart # ContractorEditingController
│   │   ├── photo_attachment_manager.dart    # PhotoAttachmentManager
│   │   ├── form_attachment_manager.dart     # FormAttachmentManager
│   │   └── pdf_data_builder.dart            # PdfDataBuilder
│   ├── screens/
│   │   ├── home_screen.dart
│   │   ├── entries_list_screen.dart
│   │   ├── drafts_list_screen.dart
│   │   ├── entry_editor_screen.dart      # Unified create + edit screen
│   │   ├── entry_review_screen.dart
│   │   ├── review_summary_screen.dart
│   │   ├── screens.dart                   # Barrel
│   │   └── report_widgets/               # Sub-module: edit-mode dialogs/sheets
│   │       ├── report_add_contractor_sheet.dart
│   │       ├── report_add_personnel_type_dialog.dart
│   │       ├── report_add_quantity_dialog.dart
│   │       ├── report_debug_pdf_actions_dialog.dart
│   │       ├── report_delete_personnel_type_dialog.dart
│   │       ├── report_location_edit_dialog.dart
│   │       ├── report_pdf_actions_dialog.dart
│   │       ├── report_photo_detail_dialog.dart
│   │       ├── report_weather_edit_dialog.dart
│   │       └── report_widgets.dart        # Barrel
│   ├── widgets/                          # Reusable sub-widgets
│   │   └── (entry_basics_section, entry_activities_section,
│   │       entry_contractors_section, entry_photos_section, entry_forms_section,
│   │       entry_quantities_section, entry_form_card, entry_action_bar,
│   │       contractor_editor_widget, bid_item_picker_sheet,
│   │       add_equipment_dialog, add_personnel_type_dialog, draft_entry_tile,
│   │       form_selection_dialog, photo_detail_dialog, review_field_row,
│   │       review_missing_warning, simple_info_row, status_badge, submitted_banner)
│   └── utils/
│       └── weather_helpers.dart
└── entries.dart                          # Feature entry point
```

## Data Layer

### Models

| Class | File | Notes |
|-------|------|-------|
| `DailyEntry` | `data/models/daily_entry.dart` | Core record; `status` enum {draft, complete, submitted}; `weather` enum; `syncStatus` for legacy field (sync now uses change_log triggers) |
| `EntryExport` | `data/models/entry_export.dart` | Export snapshot; not in models barrel |
| `Document` | `data/models/document.dart` | Document attachment; not in models barrel |

**Note:** Junction entities (EntryContractor, EntryPersonnelCounts, EntryEquipment) live in
the **contractors** feature datasources (`lib/features/contractors/data/datasources/local/`).
Their datasources (`EntryPersonnelCountsLocalDatasource`, `EntryEquipmentLocalDatasource`,
`EntryContractorsLocalDatasource`) are provisioned via `entries_providers.dart` and
exposed as `Provider.value` instances.

### Local Datasources

| Class | File | Barrel status |
|-------|------|--------------|
| `DailyEntryLocalDatasource` | `data/datasources/local/daily_entry_local_datasource.dart` | In local barrel |
| `EntryExportLocalDatasource` | `data/datasources/local/entry_export_local_datasource.dart` | Not in barrel |
| `DocumentLocalDatasource` | `data/datasources/local/document_local_datasource.dart` | Not in barrel |

### Remote Datasources

| Class | File | Barrel status |
|-------|------|--------------|
| `DailyEntryRemoteDatasource` | `data/datasources/remote/daily_entry_remote_datasource.dart` | In remote barrel |
| `DocumentRemoteDatasource` | `data/datasources/remote/document_remote_datasource.dart` | Not in barrel |
| `EntryExportRemoteDatasource` | `data/datasources/remote/entry_export_remote_datasource.dart` | Not in barrel |

### Repository Implementations

| Class | File |
|-------|------|
| `DailyEntryRepositoryImpl` | `data/repositories/daily_entry_repository.dart` |
| `EntryExportRepositoryImpl` | `data/repositories/entry_export_repository.dart` |
| `DocumentRepositoryImpl` | `data/repositories/document_repository.dart` |

## Domain Layer

### Repository Interfaces

Defined in `domain/repositories/`:
- `DailyEntryRepository` — Core CRUD + date-range queries, status queries, count
- `EntryExportRepository` — Export snapshot persistence
- `DocumentRepository` — Document attachment management

### Use Cases

All located in `domain/usecases/`:

| Class | Responsibility |
|-------|---------------|
| `SubmitEntryUseCase` | Transition entry to submitted status with signature |
| `UndoSubmitEntryUseCase` | Reverse a submitted entry back to complete |
| `BatchSubmitEntriesUseCase` | Submit multiple entries atomically |
| `ExportEntryUseCase` | Build export snapshot; depends on `ExportFormUseCase` from forms feature |
| `FilterEntriesUseCase` | Date-range, location, and status filters; also `updateStatus` / `countForProject` |
| `LoadEntriesUseCase` | Project-scoped entry loading |
| `ManageEntryUseCase` | CRUD operations on a single entry |
| `CalendarEntriesUseCase` | Calendar-view queries (entries by month/date) |

**`ExportEntryUseCase` cross-feature dependency:** Takes `ExportFormUseCase` (from the forms
feature) as a constructor parameter. The forms module must be registered in
`app_providers.dart` **before** entries (Tier 3 before Tier 4).

## Presentation Layer

### Providers

| Class | Type | Responsibility |
|-------|------|---------------|
| `DailyEntryProvider` | `ChangeNotifier` | Central state: entry list, current entry, submit/undo, batch submit, calendar queries, filter, auth-gated writes |
| `EntryExportProvider` | `ChangeNotifier` | Export state; delegates to `ExportEntryUseCase` |
| `CalendarFormatProvider` | `ChangeNotifier` | Calendar display format (month/week/2-week) |

`DailyEntryProvider` has an auth gate: `canWrite` is a callback set by `entryProviders()`
to `authProvider.canEditFieldData`. Mutation methods check this before proceeding.

### Controllers

The entry editor uses a **controller pattern** rather than direct-provider editing, keeping
transient form state separate from the persisted provider state.

| Class | Responsibility |
|-------|---------------|
| `EntryEditingController` | Holds in-progress edit state for a single DailyEntry; drives `entry_editor_screen.dart` |
| `ContractorEditingController` | Manages contractor assignment list for one entry; requires `DatabaseService` from Provider (initialized in `didChangeDependencies` with `_controllersInitialized` guard — see architecture.md Known Deviations) |
| `PhotoAttachmentManager` | Coordinates photo capture, selection, and attachment to an entry (cross-feature: photos feature) |
| `FormAttachmentManager` | Coordinates form-response attachment to an entry (cross-feature: forms feature) |
| `PdfDataBuilder` | Assembles entry data into a structure consumable by the PDF feature |

### Screens (6 total)

| Screen | Purpose |
|--------|---------|
| `HomeScreen` | Calendar + project overview; entry point for the feature |
| `EntriesListScreen` | Full entry list for a project |
| `DraftsListScreen` | Filtered view of draft entries |
| `EntryEditorScreen` | Unified create and edit screen; uses `EntryEditingController` |
| `EntryReviewScreen` | Read-only review before submission |
| `ReviewSummaryScreen` | Post-submission summary |

### Report Widgets Sub-Module

`presentation/screens/report_widgets/` — 9 dialog and sheet widgets used exclusively by
`EntryEditorScreen` in edit mode. These handle in-line editing of specific entry sections
without navigating away from the report screen:

- `ReportAddContractorSheet`
- `ReportAddPersonnelTypeDialog`
- `ReportAddQuantityDialog`
- `ReportDebugPdfActionsDialog`
- `ReportDeletePersonnelTypeDialog`
- `ReportLocationEditDialog`
- `ReportPdfActionsDialog`
- `ReportPhotoDetailDialog`
- `ReportWeatherEditDialog`

### Presentation Models

| Class | File | Purpose |
|-------|------|---------|
| `ContractorUiState` | `presentation/models/contractor_ui_state.dart` | UI-layer snapshot of contractor data for display in the editor |

## Dependency Injection

**File:** `lib/features/entries/di/entries_providers.dart`

`entryProviders()` is a factory function returning a `List<SingleChildWidget>`. It:

1. Accepts repository interfaces (`DailyEntryRepository`, `EntryExportRepository`,
   `FormResponseRepository`), `AuthProvider`, and three contractor datasource instances
   as named parameters.
2. Constructs all eight use cases inline before the returned list.
3. Registers `DailyEntryProvider`, `CalendarFormatProvider`, and `EntryExportProvider` as
   `ChangeNotifierProvider`.
4. Registers `EntryPersonnelCountsLocalDatasource`, `EntryEquipmentLocalDatasource`, and
   `EntryContractorsLocalDatasource` as `Provider.value` (owned by the contractors feature,
   re-exposed here for controller access).

**Ordering constraint:** This is Tier 4. The forms module (Tier 3) must be registered first
because `ExportEntryUseCase` reads `ExportFormUseCase` via `context.read` at
`ChangeNotifierProvider.create` time.

## Key Patterns

### Editor Controller Pattern
`EntryEditorScreen` does NOT read/write `DailyEntryProvider` directly for in-progress edits.
Instead it owns an `EntryEditingController` that holds mutable draft state. On save, the
controller flushes to the provider (which persists to SQLite).

### Submit / Undo / Batch Submit Workflow
```
Draft → (ManageEntryUseCase.markComplete) → Complete
Complete → (SubmitEntryUseCase) → Submitted
Submitted → (UndoSubmitEntryUseCase) → Complete
[Draft/Complete][] → (BatchSubmitEntriesUseCase) → Submitted[]
```

### Cross-Feature Coordination
- **Photos**: `PhotoAttachmentManager` wraps photo-feature calls
- **Forms**: `FormAttachmentManager` wraps forms-feature calls; `ExportEntryUseCase` takes
  `ExportFormUseCase` as a dep
- **PDF**: `PdfDataBuilder` assembles the payload; the PDF feature owns actual generation
- **Contractors**: Junction datasources (personnel counts, equipment, contractors) live in
  the contractors feature but are injected into entries DI

### Offline Behavior
Fully offline. All mutations write to SQLite. The sync feature reads the `change_log`
table (populated by SQLite triggers on `daily_entries` and related tables) to push changes
to Supabase. There is no per-field `syncStatus` tracking in the model — the change_log
trigger approach is authoritative.

## Feature Relationships

### Depends On
| Feature | Why |
|---------|-----|
| `projects` | `DailyEntry.projectId` FK; project context required for all queries |
| `contractors` | Junction datasources (EntryContractor, EntryPersonnelCounts, EntryEquipment) |
| `quantities` | `EntryQuantity` bid-item linkage |
| `locations` | `DailyEntry.locationId` FK |
| `photos` | Photo attachment via `PhotoAttachmentManager` |
| `weather` | Weather enum / display helpers |
| `forms` | Form attachment via `FormAttachmentManager`; `ExportFormUseCase` in export path |
| `auth` | `authProvider.canEditFieldData` gates all mutations |

### Required By
| Feature | Why |
|---------|-----|
| `sync` | Pushes `daily_entries` change_log rows to Supabase |
| `pdf` | `PdfDataBuilder` output consumed by PDF generation pipeline |
| `dashboard` | Reads entry counts / status summaries |
