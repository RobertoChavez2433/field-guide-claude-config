---
feature: contractors
type: overview
scope: Contractor, Equipment & Personnel Management
updated: 2026-03-30
---

# Contractors Feature Overview

## Purpose

The Contractors feature manages prime contractors, sub-contractors, equipment, and personnel types associated with construction projects. It enables inspectors to track who is on-site, what equipment is deployed, and what roles people fulfill. Contractors are created during project setup and referenced throughout daily entries and project documentation.

## Key Responsibilities

- **Contractor Management**: Create, edit, and delete prime and sub-contractors with optional contact information
- **Equipment Tracking**: Define equipment types per contractor, track usage per daily entry
- **Personnel Types**: Define personnel categories per contractor (e.g., "Foreman", "Laborer"), track counts in daily entries
- **Entry Associations**: Record which contractors, equipment, and personnel counts apply to a specific entry
- **Frequency Tracking**: Surface most-frequently-used contractors and equipment for quick selection in entries

## Key Files

### Local Data Sources (6)

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/contractors/data/datasources/local/contractor_local_datasource.dart` | `ContractorLocalDatasource` | SQLite CRUD + prime/sub filtering, frequency query |
| `lib/features/contractors/data/datasources/local/equipment_local_datasource.dart` | `EquipmentLocalDatasource` | SQLite CRUD + usage-sorted queries |
| `lib/features/contractors/data/datasources/local/personnel_type_local_datasource.dart` | `PersonnelTypeLocalDatasource` | SQLite CRUD + per-contractor reorder |
| `lib/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart` | `EntryContractorsLocalDatasource` | Junction table (`entry_contractors`); diff-based set, soft-delete, resurrect |
| `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart` | `EntryEquipmentLocalDatasource` | `entry_equipment` table; upsert, soft-delete, save-for-entry |
| `lib/features/contractors/data/datasources/local/entry_personnel_counts_local_datasource.dart` | `EntryPersonnelCountsLocalDatasource` | `entry_personnel_counts` table; per-contractor type counts, soft-delete |

### Remote Data Sources (4)

| File Path | Class | Supabase Table |
|-----------|-------|----------------|
| `lib/features/contractors/data/datasources/remote/contractor_remote_datasource.dart` | `ContractorRemoteDatasource` | `contractors` |
| `lib/features/contractors/data/datasources/remote/equipment_remote_datasource.dart` | `EquipmentRemoteDatasource` | `equipment` |
| `lib/features/contractors/data/datasources/remote/personnel_type_remote_datasource.dart` | `PersonnelTypeRemoteDatasource` | `personnel_types` |
| `lib/features/contractors/data/datasources/remote/entry_equipment_remote_datasource.dart` | `EntryEquipmentRemoteDatasource` | `entry_equipment` |

### Domain Repository Interfaces (3)

| File Path | Class |
|-----------|-------|
| `lib/features/contractors/domain/repositories/contractor_repository.dart` | `ContractorRepository` |
| `lib/features/contractors/domain/repositories/equipment_repository.dart` | `EquipmentRepository` |
| `lib/features/contractors/domain/repositories/personnel_type_repository.dart` | `PersonnelTypeRepository` |

### Repository Implementations (3)

| File Path | Class |
|-----------|-------|
| `lib/features/contractors/data/repositories/contractor_repository_impl.dart` | `ContractorRepositoryImpl` |
| `lib/features/contractors/data/repositories/equipment_repository_impl.dart` | `EquipmentRepositoryImpl` |
| `lib/features/contractors/data/repositories/personnel_type_repository_impl.dart` | `PersonnelTypeRepositoryImpl` |

### Providers (3)

| File Path | Class | Notes |
|-----------|-------|-------|
| `lib/features/contractors/presentation/providers/contractor_provider.dart` | `ContractorProvider` | Extends `BaseListProvider`; prime/sub helpers, frequency loader |
| `lib/features/contractors/presentation/providers/equipment_provider.dart` | `EquipmentProvider` | Extends `ChangeNotifier`; per-contractor equipment state |
| `lib/features/contractors/presentation/providers/personnel_type_provider.dart` | `PersonnelTypeProvider` | Extends `BaseListProvider`; per-contractor type state |

### Models (5)

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/contractors/data/models/contractor.dart` | `Contractor` / `ContractorType` | Prime or sub contractor; enum `{prime, sub}` |
| `lib/features/contractors/data/models/equipment.dart` | `Equipment` | Equipment definition owned by a contractor |
| `lib/features/contractors/data/models/personnel_type.dart` | `PersonnelType` | Personnel category (e.g., "Foreman"); per-contractor with sort order |
| `lib/features/contractors/data/models/entry_equipment.dart` | `EntryEquipment` | Entry-equipment junction with `wasUsed` flag |
| `lib/features/contractors/data/models/entry_personnel.dart` | `EntryPersonnel` | Legacy fixed-column personnel record (pre-dynamic-counts) |

## Screens

**No dedicated screens.** All contractor, equipment, and personnel UI is embedded inside the `entries` and `projects` feature screens. There are no standalone routes for this feature.

## Data Sources

- **SQLite (local)**: Persists all contractors, equipment, personnel types, and entry-level assignments (`entry_contractors`, `entry_equipment`, `entry_personnel_counts`)
- **Supabase (remote)**: Mirrors four core tables (`contractors`, `equipment`, `personnel_types`, `entry_equipment`) via the sync engine

## Integration Points

**Required by:**
- `entries` — Entry screens embed contractor selection, equipment usage, and personnel count tracking
- `projects` — Project setup creates and manages contractors, equipment, and personnel types

**Depends on:**
- `projects` — Contractors are scoped to a project (`project_id` foreign key on all core tables)
- `core/database` — SQLite schema for all contractor-related tables

## Offline Behavior

Contractors are **fully offline-capable**. Creation, editing, and assignment to entries occur entirely offline. All data persists in SQLite. SQLite triggers auto-populate `change_log` on any write; the sync engine pushes those changes to Supabase during the next sync cycle.

## Edge Cases & Limitations

- **Contractor Deletion**: Soft-delete only; entries referencing a deleted contractor remain accessible
- **Entry Contractors**: Diff-based `setForEntry` avoids unnecessary change_log entries for unchanged rows
- **Personnel Counts**: Stored dynamically in `entry_personnel_counts` (contractor × type × count); `EntryPersonnel` model is legacy (fixed columns, pre-migration)
- **Equipment Hours**: Not tracked; `entry_equipment` records presence (`wasUsed` flag) only, not hours
- **Personnel Types**: Scoped per contractor; `contractorId` is nullable on `PersonnelType` for legacy project-level rows
- **Contact Information**: `phone` and `contactName` are optional; no phone format validation
- **ContractorType**: Enum `{prime, sub}` only; no custom types

## Detailed Specifications

See `rules/database/schema-patterns.md` for:
- SQLite schema for contractors, equipment, personnel types, and junction tables
- Foreign key relationships and cascade behavior
