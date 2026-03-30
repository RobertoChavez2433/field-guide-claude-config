---
feature: contractors
type: architecture
scope: Contractor, Equipment & Personnel Management
updated: 2026-03-30
---

# Contractors Feature Architecture

## Overview

Data-only feature — no screens. Provides domain entities (Contractor, Equipment, PersonnelType) and entry-scoped junction tables consumed by the entries and projects features. All UI is embedded in those consuming features.

## Layer Structure

```
lib/features/contractors/
├── data/
│   ├── models/
│   │   ├── models.dart                          # Barrel export
│   │   ├── contractor.dart                      # Contractor, ContractorType enum
│   │   ├── equipment.dart                       # Equipment
│   │   ├── personnel_type.dart                  # PersonnelType
│   │   ├── entry_personnel.dart                 # EntryPersonnel (legacy fixed-field counts)
│   │   └── entry_equipment.dart                 # EntryEquipment (wasUsed flag, soft-delete)
│   ├── datasources/
│   │   ├── datasources.dart                     # Barrel
│   │   ├── local/
│   │   │   ├── local_datasources.dart           # Barrel
│   │   │   ├── contractor_local_datasource.dart
│   │   │   ├── equipment_local_datasource.dart
│   │   │   ├── personnel_type_local_datasource.dart
│   │   │   ├── entry_contractors_local_datasource.dart   # Also defines EntryContractor model
│   │   │   ├── entry_equipment_local_datasource.dart
│   │   │   └── entry_personnel_counts_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart          # Barrel
│   │       ├── contractor_remote_datasource.dart
│   │       ├── equipment_remote_datasource.dart
│   │       ├── personnel_type_remote_datasource.dart
│   │       └── entry_equipment_remote_datasource.dart
│   └── repositories/
│       ├── repositories.dart                    # Barrel
│       ├── contractor_repository_impl.dart      # ContractorRepositoryImpl
│       ├── equipment_repository_impl.dart       # EquipmentRepositoryImpl
│       └── personnel_type_repository_impl.dart  # PersonnelTypeRepositoryImpl
├── domain/
│   ├── domain.dart                              # Barrel
│   └── repositories/
│       ├── repositories.dart                    # Barrel
│       ├── contractor_repository.dart           # ContractorRepository (abstract)
│       ├── equipment_repository.dart            # EquipmentRepository (abstract)
│       └── personnel_type_repository.dart       # PersonnelTypeRepository (abstract)
├── presentation/
│   ├── presentation.dart                        # Barrel
│   └── providers/
│       ├── providers.dart                       # Barrel
│       ├── contractor_provider.dart             # ContractorProvider
│       ├── equipment_provider.dart              # EquipmentProvider
│       └── personnel_type_provider.dart         # PersonnelTypeProvider
├── di/
│   └── contractors_providers.dart              # contractorProviders() function
└── contractors.dart                            # Feature entry point (barrel)
```

## Data Layer

### Models

| Class | File | Key Fields | Notes |
|-------|------|------------|-------|
| `Contractor` | `contractor.dart` | id, projectId, name, type (ContractorType), contactName?, phone?, createdByUserId? | `isPrime`/`isSub` getters; `ContractorType.{prime,sub}` enum |
| `Equipment` | `equipment.dart` | id, contractorId, name, description?, createdByUserId? | Scoped to contractor (not project directly) |
| `PersonnelType` | `personnel_type.dart` | id, projectId, contractorId?, name, shortCode?, sortOrder, createdByUserId? | contractorId nullable — null = legacy project-level type; `displayCode` getter |
| `EntryPersonnel` | `entry_personnel.dart` | id, entryId, contractorId, foremanCount, operatorCount, laborerCount | Legacy fixed-field model; `totalCount` getter |
| `EntryEquipment` | `entry_equipment.dart` | id, entryId, equipmentId, wasUsed, projectId?, createdByUserId?, deletedAt?, deletedBy? | Soft-delete support |
| `EntryContractor` | `entry_contractors_local_datasource.dart` | id, entryId, contractorId, projectId?, createdByUserId? | Model defined alongside its datasource; deterministic ID `ec-{entryId}-{contractorId}` |

Note: The `models.dart` barrel does NOT export `EntryContractor` (it lives in the datasource file). It exports: Contractor, Equipment, PersonnelType, EntryPersonnel, EntryEquipment.

### Local Datasources

| Class | Table | Notes |
|-------|-------|-------|
| `ContractorLocalDatasource` | `contractors` | `getPrimeByProjectId`, `getSubsByProjectId`, `getMostFrequentIds`, paginated queries |
| `EquipmentLocalDatasource` | `equipment` | Scoped by `contractorId`; `getByContractorIdSortedByUsage`, `getUsageCountsByProject` |
| `PersonnelTypeLocalDatasource` | `personnel_types` | `getByContractor`, `reorderTypes`, `getNextSortOrder*` |
| `EntryContractorsLocalDatasource` | `entry_contractors` | Diff-based `setForEntry`; soft-delete with resurrection; deterministic IDs |
| `EntryEquipmentLocalDatasource` | `entry_equipment` | Soft-delete support |
| `EntryPersonnelCountsLocalDatasource` | `entry_personnel_counts` | Dynamic per-type counts (replaces legacy fixed-field `EntryPersonnel`); upsert/resurrection pattern; deterministic ID `epc-{entryId}-{contractorId}-{typeId}` |

### Remote Datasources

All extend `BaseRemoteDatasource<T>` from `shared/datasources/`:

| Class | Supabase Table |
|-------|---------------|
| `ContractorRemoteDatasource` | `contractors` |
| `EquipmentRemoteDatasource` | `equipment` |
| `PersonnelTypeRemoteDatasource` | `personnel_types` |
| `EntryEquipmentRemoteDatasource` | `entry_equipment` |

No remote datasource exists for `entry_contractors` or `entry_personnel_counts` — those are synced via the change_log trigger mechanism, not direct remote DS calls.

### Repository Implementations

All `*RepositoryImpl` classes take only a local datasource (no remote DS injected directly). Remote sync is handled by the sync engine via change_log triggers.

| Class | Interface | Local DS dependency |
|-------|-----------|---------------------|
| `ContractorRepositoryImpl` | `ContractorRepository` | `ContractorLocalDatasource` |
| `EquipmentRepositoryImpl` | `EquipmentRepository` | `EquipmentLocalDatasource` |
| `PersonnelTypeRepositoryImpl` | `PersonnelTypeRepository` | `PersonnelTypeLocalDatasource` |

`ContractorRepositoryImpl` validates unique names within project on create/update via `UniqueNameValidator`.

## Domain Layer

### Repository Interfaces

**`ContractorRepository`** (`implements ProjectScopedRepository<Contractor>`):
- `getPrimeByProjectId(String projectId)`
- `getSubsByProjectId(String projectId)`
- `updateContractor(Contractor)` → `RepositoryResult<Contractor>`
- `deleteByProjectId(String projectId)`
- `insertAll(List<Contractor>)`
- `getMostFrequentIds(String projectId, {int limit})`

**`EquipmentRepository`** (`implements BaseRepository<Equipment>`):
- `getByContractorId(String contractorId)`
- `getByContractorIds(List<String>)`
- `create(Equipment)` → `RepositoryResult<Equipment>`
- `updateEquipment(Equipment)` → `RepositoryResult<Equipment>`
- `deleteByContractorId(String contractorId)`
- `getCountByContractor(String contractorId)`
- `getByContractorIdSortedByUsage(String contractorId, String projectId)`
- `getUsageCountsByProject(String projectId)`
- `insertAll(List<Equipment>)`

**`PersonnelTypeRepository`** (`implements ProjectScopedRepository<PersonnelType>`):
- `getByContractor(String projectId, String contractorId)`
- `updateType(PersonnelType)` → `RepositoryResult<PersonnelType>`
- `deleteByProjectId(String projectId)`
- `reorderTypes(String projectId, List<String> orderedIds)`
- `getNextSortOrderForContractor(String projectId, String contractorId)`
- `getNextSortOrder(String projectId)`
- `insertAll(List<PersonnelType>)`

No domain use cases exist in this feature — logic lives directly in providers and repository impls.

## Presentation Layer

### Providers

**`ContractorProvider`** extends `BaseListProvider<Contractor, ContractorRepository>`:
- State: `items` (inherited), `_frequentContractorIds`
- Key getters: `contractors`, `primeContractor` (single?), `subcontractors`, `frequentContractorIds`, `hasContractors`, `contractorCount`
- Sort: prime first, then alphabetical by name
- Write methods (all guarded by `canWrite()`): `createContractor`, `updateContractor`, `deleteContractor`
- Load methods: `loadContractors(projectId)`, `loadFrequentContractorIds(projectId)`

**`EquipmentProvider`** extends `ChangeNotifier` directly (not BaseListProvider):
- State: `_equipmentByContractor` (Map<String, List<Equipment>>), `_isLoading`, `_error`
- Key getters: `equipmentByContractor`, `allEquipment` (flat), `getEquipmentForContractor(id)`, `getEquipmentCount(id)`
- Load methods: `loadEquipmentForContractor`, `loadEquipmentForContractors`, `loadEquipmentForContractorsSortedByUsage`
- Write methods (all guarded by `canWrite()`): `createEquipment`, `updateEquipment`, `deleteEquipment(id, contractorId)`, `deleteEquipmentForContractor`

**`PersonnelTypeProvider`** extends `BaseListProvider<PersonnelType, PersonnelTypeRepository>`:
- State: `items` (inherited), `_contractorTypesCache` (Map<String, List<PersonnelType>>)
- Sort: by `sortOrder`
- Key getters: `types`, `getTypeById`, `getTypeByShortCode`, `getTypeByName`, `getTypesForContractor`
- Load methods: `loadTypesForProject(projectId)`, `loadTypesForContractor(projectId, contractorId)`
- Cache: `getCachedTypesForContractor`, `clearContractorCache`
- Write methods (all guarded by `canWrite()`): `createType`, `updateType`, `deleteType`
- Special: `createDefaultTypesForContractor` (creates Foreman/Laborer/Operator if none exist), `reorderTypes`

### canWrite Guard

All three providers expose a `canWrite` callback (`bool Function() canWrite = () => true`). The DI wires it to `authProvider.canEditFieldData`.

## DI Wiring

`lib/features/contractors/di/contractors_providers.dart` exports a single top-level function:

```dart
List<SingleChildWidget> contractorProviders({
  required ContractorRepository contractorRepository,
  required EquipmentRepository equipmentRepository,
  required PersonnelTypeRepository personnelTypeRepository,
  required AuthProvider authProvider,
})
```

This is **Tier 4** in the provider registration order (declared in a comment in the file). It wires `canWrite` on each provider to `authProvider.canEditFieldData`.

## Junction Tables & Entry-Scoped Tracking

| Table | Local DS | Managed By | Notes |
|-------|----------|------------|-------|
| `entry_contractors` | `EntryContractorsLocalDatasource` | Entries feature | Diff-based `setForEntry`; soft-delete with resurrection |
| `entry_equipment` | `EntryEquipmentLocalDatasource` | Entries feature | `wasUsed` boolean; soft-delete |
| `entry_personnel_counts` | `EntryPersonnelCountsLocalDatasource` | Entries feature | Dynamic per-type counts keyed by (entryId, contractorId, typeId); replaces legacy `entry_personnel` fixed-field table |

The local datasources for these junction tables live inside the contractors feature but are consumed by the entries feature. They are NOT exposed through repository interfaces — entries accesses them directly via DI.

## Offline Behavior

Fully offline. All reads/writes go to SQLite. No network calls at write time. Sync happens asynchronously via the change_log trigger mechanism in `lib/core/database/database_service.dart`. The remote datasources exist for pull-down scenarios only (e.g., initial sync, re-sync).

## Relationships

```
Project (1)
    ├─→ Contractor[] — prime and subs; scoped by projectId
    │       └─→ Equipment[] — scoped to each contractor (contractorId FK)
    │               └─→ EntryEquipment[] — wasUsed flag per daily entry
    │
    ├─→ PersonnelType[] — scoped by projectId+contractorId; sortable
    │
    └─→ EntryContractor[] — which contractors were on-site per entry
            └─→ EntryPersonnelCounts[] — dynamic headcounts per contractor+type per entry
```

**Consumed by:**
- `entries` feature — reads contractors/equipment/personnel for editing; writes to junction tables
- `projects` feature — reads for project setup screens

**Depends on:**
- `auth` feature — `AuthProvider.canEditFieldData` for write guard
- `core/database` — `DatabaseService` for all SQLite access
