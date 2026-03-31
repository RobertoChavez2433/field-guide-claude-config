# Pattern: Soft Delete

## How We Do It
Records are never physically deleted by default. `GenericLocalDatasource.delete()` delegates to `softDelete()` which sets `deleted_at` and `deleted_by` timestamps. Hard deletes only happen in `SoftDeleteService.purgeExpiredRecords()` (after 30-day retention) or `hardDeleteWithSync()` ("Delete Forever" from Trash). Both suppress triggers via `sync_control.pulling='1'` and manually insert change_log entries for remote propagation. Cascade deletes flow parent→children within transactions.

## Exemplars

### GenericLocalDatasource.softDelete (lib/shared/datasources/generic_local_datasource.dart:121)
```dart
Future<void> softDelete(String id, {String? userId}) async {
  final database = await db.database;
  final now = DateTime.now().toUtc().toIso8601String();
  await database.update(tableName, {
    'deleted_at': now, 'deleted_by': userId, 'updated_at': now,
  }, where: 'id = ?', whereArgs: [id]);
  Logger.db('SOFT_DELETE $tableName id=$id');
}
```

### SoftDeleteService.cascadeSoftDeleteProject (lib/services/soft_delete_service.dart:71)
Cascades soft-delete through all child tables in a transaction. When `rpcSucceeded=true`, cleans change_log and unenrolls from synced_projects. When `rpcSucceeded=false`, KEEPS change_log so sync engine can push later.

### GenericLocalDatasource._whereWithDeletedFilter (generic_local_datasource.dart:46)
All queries in GenericLocalDatasource automatically append `deleted_at IS NULL` filter.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `softDelete` | generic_local_datasource.dart:121 | `Future<void> softDelete(String id, {String? userId})` | Single record soft-delete |
| `hardDelete` | generic_local_datasource.dart:155 | `Future<void> hardDelete(String id)` | Permanent removal (purge/trash) |
| `restore` | generic_local_datasource.dart:138 | `Future<void> restore(String id)` | Undo soft-delete |
| `getDeleted` | generic_local_datasource.dart:166 | `Future<List<T>> getDeleted()` | List trash items |
| `cascadeSoftDeleteProject` | soft_delete_service.dart:71 | `Future<void> cascadeSoftDeleteProject(String projectId, {String? userId, bool rpcSucceeded = false})` | Delete project + all children |
| `cascadeSoftDeleteEntry` | soft_delete_service.dart:207 | `Future<void> cascadeSoftDeleteEntry(String entryId, {String? userId})` | Delete entry + children |
| `restoreWithCascade` | soft_delete_service.dart:267 | `Future<void> restoreWithCascade(String tableName, String id)` | Restore + parent cascade |
| `purgeExpiredRecords` | soft_delete_service.dart:399 | `Future<int> purgeExpiredRecords({int retentionDays = 30, DateTime? lastSyncTime})` | 30-day cleanup |
| `hardDeleteWithSync` | soft_delete_service.dart:524 | `Future<void> hardDeleteWithSync(String tableName, String id)` | "Delete Forever" with sync |

## Imports
```dart
import 'package:construction_inspector/services/soft_delete_service.dart';
import 'package:construction_inspector/shared/datasources/generic_local_datasource.dart';
```

## Lint Rules Targeting This Pattern
- D1: `avoid_raw_database_delete` — no database.delete() outside SoftDeleteService/GenericLocalDatasource/sync engine
- D2: `require_soft_delete_filter` — raw queries must include `deleted_at IS NULL`
