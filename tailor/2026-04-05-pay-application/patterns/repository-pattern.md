# Pattern: Repository

## How We Do It
Abstract repositories live in `domain/repositories/` and implement `BaseRepository<T>` or `ProjectScopedRepository<T>`. Implementations in `data/repositories/` delegate to a local datasource and wrap results in `RepositoryResult<T>` for error handling. Methods use try/catch and return `RepositoryResult.success()` or `RepositoryResult.failure()`.

## Exemplars

### FormExportRepository interface (`lib/features/forms/domain/repositories/form_export_repository.dart`)
```dart
abstract class FormExportRepository implements BaseRepository<FormExport> {
  Future<RepositoryResult<FormExport>> create(FormExport formExport);
  Future<FormExport?> getById(String id);
  Future<List<FormExport>> getAll();
  Future<void> save(FormExport item);
  Future<void> delete(String id);
  Future<List<FormExport>> getByProjectId(String projectId);
  Future<List<FormExport>> getByEntryId(String entryId);
  Future<List<FormExport>> getByFormResponseId(String formResponseId);
}
```

### FormExportRepositoryImpl (`lib/features/forms/data/repositories/form_export_repository.dart`)
```dart
class FormExportRepositoryImpl implements FormExportRepository {
  FormExportRepositoryImpl(this._localDatasource);
  final FormExportLocalDatasource _localDatasource;

  @override Future<FormExport?> getById(String id) async { ... }
  @override Future<RepositoryResult<FormExport>> create(FormExport formExport) async {
    try {
      await _localDatasource.insert(formExport);
      return RepositoryResult.success(formExport);
    } on Exception catch (e) {
      return RepositoryResult.failure('Failed to create form export: $e');
    }
  }
}
```

## Reusable Methods (from BaseRepository<T>)

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `getById` | `base_repository.dart:10` | `Future<T?> getById(String id)` | Single record fetch |
| `getAll` | `base_repository.dart:14` | `Future<List<T>> getAll()` | All records |
| `getPaged` | `base_repository.dart:17` | `Future<PagedResult<T>> getPaged({required int offset, required int limit})` | Paginated |
| `getCount` | `base_repository.dart:20` | `Future<int> getCount()` | Total count |
| `save` | `base_repository.dart:23` | `Future<void> save(T item)` | Insert or update |
| `delete` | `base_repository.dart:27` | `Future<void> delete(String id)` | Soft-delete |

## Imports
```dart
import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/shared/models/repository_result.dart';
import 'package:construction_inspector/features/<feature>/data/models/<model>.dart';
```
