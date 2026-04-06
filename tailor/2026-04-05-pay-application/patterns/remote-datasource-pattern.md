# Pattern: Remote Datasource

## How We Do It
Remote datasources extend `BaseRemoteDatasource<T>` and wrap Supabase client operations. They override `tableName`, `fromMap`, `toMap`. Base class provides `getById`, `getAll`, `insert`, `update`, `upsert`, `delete`, `insertAll`, `upsertAll`, `getUpdatedAfter`, `getCreatedAfter`, `getCount`, `getPaged`. Used by sync engine for push/pull, not called directly by repositories.

## Exemplars

### FormExportRemoteDatasource (`lib/features/forms/data/datasources/remote/form_export_remote_datasource.dart`)
```dart
class FormExportRemoteDatasource extends BaseRemoteDatasource<FormExport> {
  FormExportRemoteDatasource(super.supabase);
  @override String get tableName => 'form_exports';
  @override FormExport fromMap(Map<String, dynamic> map) => FormExport.fromMap(map);
  @override Map<String, dynamic> toMap(FormExport item) => item.toMap();
}
```

## Reusable Methods (from BaseRemoteDatasource)

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `getAll` | `base_remote_datasource.dart:41` | `Future<List<T>> getAll({String? companyId})` | All records with optional company filter |
| `getUpdatedAfter` | `base_remote_datasource.dart:99` | `Future<List<T>> getUpdatedAfter(DateTime timestamp)` | Incremental sync pull |
| `upsertAll` | `base_remote_datasource.dart:91` | `Future<void> upsertAll(List<T> items)` | Batch sync push |

## Imports
```dart
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:construction_inspector/shared/datasources/base_remote_datasource.dart';
```
