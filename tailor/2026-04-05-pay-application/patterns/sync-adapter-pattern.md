# Pattern: Sync Adapter

## How We Do It
Simple tables use `AdapterConfig` (data-driven, 13 of 22 adapters). Complex tables with custom logic use dedicated adapter classes extending `TableAdapter`. All adapters are registered in FK dependency order in `sync_registry.dart`. File-syncing adapters set `isFileAdapter: true` with a `buildStoragePath` function and `storageBucket`.

## Exemplars

### AdapterConfig for form_exports (`lib/features/sync/adapters/simple_adapters.dart:163`)
```dart
AdapterConfig(
  table: 'form_exports',
  scope: ScopeType.viaProject,
  fkDeps: ['projects', 'form_responses'],
  fkColumnMap: {
    'projects': 'project_id',
    'form_responses': 'form_response_id',
  },
  localOnlyColumns: ['file_path'],
  isFileAdapter: true,
  storageBucket: 'form-exports',
  stripExifGps: false,
  buildStoragePath: _buildFormExportPath,
  extractRecordName: _extractExportRecordName,
),
```

### AdapterConfig for entry_exports (`lib/features/sync/adapters/simple_adapters.dart:144`)
```dart
AdapterConfig(
  table: 'entry_exports',
  scope: ScopeType.viaEntry,
  fkDeps: ['daily_entries', 'projects'],
  fkColumnMap: {
    'daily_entries': 'entry_id',
    'projects': 'project_id',
  },
  localOnlyColumns: ['file_path'],
  isFileAdapter: true,
  storageBucket: 'entry-exports',
  stripExifGps: false,
  buildStoragePath: _buildEntryExportPath,
  extractRecordName: _extractExportRecordName,
),
```

### Registration Order (`lib/features/sync/engine/sync_registry.dart:31-54`)
```
projects -> project_assignments -> locations -> contractors -> Equipment -> bid_items ->
personnel_types -> DailyEntry -> Photo -> EntryEquipment -> entry_quantities ->
entry_contractors -> entry_personnel_counts -> InspectorForm -> FormResponse ->
form_exports -> entry_exports -> Document -> todo_items -> calculation_history ->
SupportTicket -> ConsentRecord
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `AdapterConfig.toAdapter()` | `adapter_config.dart:97` | `TableAdapter toAdapter()` | Convert config to runtime adapter |
| `SyncRegistry.registerAdapters` | `sync_registry.dart:78` | `void registerAdapters(List<TableAdapter> adapterList)` | Register all adapters |

## Where to Insert New Adapters
For `export_artifacts`: after `form_exports` and before `entry_exports` (or after `entry_exports`). It has FK to `projects` only.
For `pay_applications`: after `export_artifacts`. It has FK to `export_artifacts` + `projects` + self-referential `previous_application_id`.

## Imports
```dart
import 'package:construction_inspector/features/sync/adapters/adapter_config.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';
```
