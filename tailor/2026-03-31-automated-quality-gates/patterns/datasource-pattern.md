# Pattern: Generic Local Datasource

## How We Do It
All local data access goes through `GenericLocalDatasource<T>` — an abstract base class with 23 methods covering CRUD, soft-delete, pagination, and bulk operations. Concrete datasources extend it and implement `tableName`, `fromMap`, `toMap`, `getId`, `defaultOrderBy`. A `_whereWithDeletedFilter` method automatically appends `deleted_at IS NULL` to all standard queries. Project-scoped entities extend `ProjectScopedDatasource<T>` which adds a `currentProjectId` filter.

## Exemplars

### GenericLocalDatasource (lib/shared/datasources/generic_local_datasource.dart:22)
Abstract class implementing `BaseLocalDatasource<T>`. Key methods: `getById`, `getAll`, `insert`, `update`, `delete` (→softDelete), `softDelete`, `hardDelete`, `restore`, `getDeleted`, `purgeExpired`, `insertAll`, `getWhere`, `countWhere`, `getCount`, `getPaged`.

### ProjectScopedDatasource (lib/shared/datasources/project_scoped_datasource.dart:15)
Extends GenericLocalDatasource, adds project_id scoping to queries.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `getById` | generic_local_datasource.dart:54 | `Future<T?> getById(String id)` | Single record fetch |
| `getAll` | generic_local_datasource.dart:81 | `Future<List<T>> getAll()` | All non-deleted records |
| `insert` | generic_local_datasource.dart:92 | `Future<void> insert(T item)` | Create record |
| `update` | generic_local_datasource.dart:99 | `Future<void> update(T item)` | Update record |
| `delete` | generic_local_datasource.dart:111 | `Future<void> delete(String id)` | Delegates to softDelete |
| `getWhere` | generic_local_datasource.dart:211 | `Future<List<T>> getWhere({required String where, required List<Object?> whereArgs, ...})` | Custom filtered query |
| `getPaged` | generic_local_datasource.dart:252 | `Future<PagedResult<T>> getPaged({required int offset, required int limit, ...})` | Paginated query |
| `insertAll` | generic_local_datasource.dart:196 | `Future<void> insertAll(List<T> items)` | Bulk insert |

## Concrete Implementations (19 total)

**Direct extends GenericLocalDatasource (8):**
CalculationHistoryLocalDatasource, EntryEquipmentLocalDatasource, EquipmentLocalDatasource, FormResponseLocalDatasource, InspectorFormLocalDatasource, ProjectLocalDatasource, EntryQuantityLocalDatasource, TodoItemLocalDatasource

**Via ProjectScopedDatasource (11):**
ContractorLocalDatasource, PersonnelTypeLocalDatasource, DailyEntryLocalDatasource, DocumentLocalDatasource, EntryExportLocalDatasource, FormExportLocalDatasource, LocationLocalDatasource, PhotoLocalDatasource, BidItemLocalDatasource

## Imports
```dart
import 'package:construction_inspector/shared/datasources/generic_local_datasource.dart';
import 'package:construction_inspector/shared/datasources/project_scoped_datasource.dart';
import 'package:construction_inspector/core/database/database_service.dart';
```

## Lint Rules Targeting This Pattern
- D1: `avoid_raw_database_delete` — use SoftDeleteService or GenericLocalDatasource methods
- D2: `require_soft_delete_filter` — raw queries must include deleted_at IS NULL
- D4: `tomap_field_completeness` — toMap() must include all constructor params
- A3: `no_raw_sql_in_presentation` — no db.query/rawQuery in presentation/
