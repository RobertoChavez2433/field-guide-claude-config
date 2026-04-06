# Pattern: Local Datasource

## How We Do It
Local datasources extend `ProjectScopedDatasource<T>` (for project-scoped tables) or `GenericLocalDatasource<T>` (for global tables). They override `tableName`, `defaultOrderBy`, `fromMap`, `toMap`, `getId`. Custom query methods use `getWhere()` or direct `database.query()`. All reads auto-filter `deleted_at IS NULL`.

## Exemplars

### FormExportLocalDatasource (`lib/features/forms/data/datasources/local/form_export_local_datasource.dart`)
```dart
class FormExportLocalDatasource extends ProjectScopedDatasource<FormExport> {
  FormExportLocalDatasource(this.db);
  @override final DatabaseService db;
  @override String get tableName => 'form_exports';
  @override String get defaultOrderBy => 'exported_at DESC';
  @override FormExport fromMap(Map<String, dynamic> map) => FormExport.fromMap(map);
  @override Map<String, dynamic> toMap(FormExport item) => item.toMap();
  @override String getId(FormExport item) => item.id;

  Future<List<FormExport>> getByFormResponseId(String formResponseId) { ... }
  Future<List<FormExport>> getByEntryId(String entryId) { ... }
  Future<void> softDeleteByFormResponseId(String formResponseId, {String? userId}) { ... }
}
```

## Reusable Methods (from ProjectScopedDatasource)

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `getByProjectId` | `project_scoped_datasource.dart:20` | `Future<List<T>> getByProjectId(String projectId)` | Load all items for a project |
| `getByProjectIdPaged` | `project_scoped_datasource.dart:25` | `Future<PagedResult<T>> getByProjectIdPaged(String projectId, {required int offset, required int limit})` | Paginated project items |
| `getCountByProject` | `project_scoped_datasource.dart:55` | `Future<int> getCountByProject(String projectId)` | Count items per project |
| `softDeleteByProjectId` | `project_scoped_datasource.dart:64` | `Future<void> softDeleteByProjectId(String projectId, {String? userId})` | Cascade soft-delete |
| `getDeletedByProjectId` | `project_scoped_datasource.dart:83` | `Future<List<T>> getDeletedByProjectId(String projectId)` | Trash screen |
| `getWhere` | `generic_local_datasource.dart` | `Future<List<T>> getWhere({required String where, List<Object?>? whereArgs})` | Custom filtered queries |

## Imports
```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/datasources/project_scoped_datasource.dart';
import 'package:construction_inspector/features/<feature>/data/models/<model>.dart';
```
