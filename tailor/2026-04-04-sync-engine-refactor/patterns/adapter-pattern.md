# Pattern: Table Adapter

## How We Do It

Each syncable table has a concrete `TableAdapter` subclass that declares its sync configuration — FK ordering, scope type, type converters, and column filtering. Adapters are pure configuration + conversion objects; the SyncEngine handles all I/O. The 22 adapters are registered in FK dependency order via `registerSyncAdapters()` in `sync_registry.dart`.

## Exemplars

### ContractorAdapter (Simple — data-driven candidate)

```dart
// lib/features/sync/adapters/contractor_adapter.dart
class ContractorAdapter extends TableAdapter {
  @override
  String get tableName => 'contractors';

  @override
  ScopeType get scopeType => ScopeType.viaProject;

  @override
  List<String> get fkDependencies => const ['projects'];

  @override
  Map<String, String> get fkColumnMap => const {'projects': 'project_id'};
}
```

### PhotoAdapter (Complex — retains as class)

```dart
// lib/features/sync/adapters/photo_adapter.dart
class PhotoAdapter extends TableAdapter {
  @override
  String get tableName => 'photos';
  @override
  ScopeType get scopeType => ScopeType.viaEntry;
  @override
  List<String> get fkDependencies => const ['daily_entries', 'projects'];
  @override
  Map<String, String> get fkColumnMap => const {
    'daily_entries': 'entry_id',
    'projects': 'project_id',
  };
  @override
  List<String> get localOnlyColumns => const ['file_path'];
  @override
  bool get isFileAdapter => true;
  @override
  String get storageBucket => 'entry-photos';
  @override
  bool get stripExifGps => true;

  @override
  String buildStoragePath(String companyId, Map<String, dynamic> localRecord) {
    final entryId = localRecord['entry_id'] as String;
    final filename = localRecord['filename'] as String;
    final safeName = filename
        .replaceAll(RegExp(r'[/\\]'), '_')
        .replaceAll(RegExp(r'\.{2,}'), '_');
    return 'entries/$companyId/$entryId/$safeName';
  }

  @override
  Future<void> validate(Map<String, dynamic> record) async {
    final filePath = record['file_path'] as String?;
    final remotePath = record['remote_path'] as String?;
    if ((filePath == null || filePath.isEmpty) &&
        (remotePath == null || remotePath.isEmpty)) {
      throw StateError(
        'PhotoAdapter: photo ${record['id']} has no file_path and no remote_path',
      );
    }
  }

  @override
  String extractRecordName(Map<String, dynamic> record) {
    return record['filename']?.toString() ??
        record['caption']?.toString() ??
        record['id']?.toString() ??
        'Unknown';
  }
}
```

### ConsentRecordAdapter (Complex — retains as class)

```dart
// lib/features/sync/adapters/consent_record_adapter.dart
class ConsentRecordAdapter extends TableAdapter {
  @override
  String get tableName => 'user_consent_records';
  @override
  ScopeType get scopeType => ScopeType.direct;
  @override
  Map<String, dynamic> pullFilter(String companyId, String userId) {
    return {'user_id': userId};
  }
  @override
  List<String> get fkDependencies => const [];
  @override
  bool get supportsSoftDelete => false;
  @override
  bool get insertOnly => true;
  @override
  bool get skipPull => true;
  @override
  bool get skipIntegrityCheck => true;
  @override
  String extractRecordName(Map<String, dynamic> record) {
    final type = record['policy_type']?.toString() ?? 'unknown';
    final version = record['policy_version']?.toString() ?? '?';
    return '$type v$version';
  }
}
```

## Adapter Classification for Data-Driven Config

### Simple (13) — data-driven candidates

| Adapter | tableName | scopeType | fkDeps | Extra Overrides |
|---------|-----------|-----------|--------|-----------------|
| ContractorAdapter | contractors | viaProject | [projects] | fkColumnMap |
| LocationAdapter | locations | viaProject | [projects] | fkColumnMap |
| BidItemAdapter | bid_items | viaProject | [projects] | fkColumnMap |
| PersonnelTypeAdapter | personnel_types | viaProject | [projects] | fkColumnMap |
| EntryContractorsAdapter | entry_contractors | viaEntry | [daily_entries, contractors] | fkColumnMap |
| EntryPersonnelCountsAdapter | entry_personnel_counts | viaEntry | [daily_entries, personnel_types] | fkColumnMap |
| EntryQuantitiesAdapter | entry_quantities | viaEntry | [daily_entries, bid_items] | fkColumnMap |
| TodoItemAdapter | todo_items | viaProject | [projects] | fkColumnMap |
| ProjectAdapter | projects | direct | [] | naturalKeyColumns |
| ProjectAssignmentAdapter | project_assignments | direct | [projects] | fkColumnMap |
| EntryExportAdapter | entry_exports | viaEntry | [daily_entries] | isFileAdapter, storageBucket, fkColumnMap |
| FormExportAdapter | form_exports | viaEntry | [form_responses] | isFileAdapter, storageBucket, fkColumnMap |
| CalculationHistoryAdapter | calculation_history | viaProject | [projects] | converters |

### Complex (9) — retain as classes (have custom logic)

| Adapter | Why Custom |
|---------|-----------|
| PhotoAdapter | Custom validate(), buildStoragePath(), extractRecordName() |
| DocumentAdapter | Custom buildStoragePath(), file adapter |
| DailyEntryAdapter | userStampColumns, custom extractRecordName() |
| EquipmentAdapter | converters with custom logic |
| EntryEquipmentAdapter | converters |
| InspectorFormAdapter | shouldSkipPush(), includesNullProjectBuiltins |
| FormResponseAdapter | converters with jsonb handling |
| ConsentRecordAdapter | Custom pullFilter(), insertOnly, skipPull, skipIntegrityCheck |
| SupportTicketAdapter | Custom pullFilter(), skipIntegrityCheck |

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| convertForRemote | table_adapter.dart:125 | `Map<String, dynamic> convertForRemote(Map<String, dynamic> local)` | Before push: strip localOnlyColumns, apply converters |
| convertForLocal | table_adapter.dart:148 | `Map<String, dynamic> convertForLocal(Map<String, dynamic> remote)` | After pull: strip remoteOnlyColumns, apply converters |
| shouldSkipPush | table_adapter.dart:84 | `bool shouldSkipPush(Map<String, dynamic> localRecord)` | Check before routing each push record |
| pullFilter | table_adapter.dart:55 | `Map<String, dynamic> pullFilter(String companyId, String userId)` | Build Supabase pull filter for ScopeType.direct |
| validate | table_adapter.dart:170 | `Future<void> validate(Map<String, dynamic> record)` | Pre-push validation |
| buildStoragePath | table_adapter.dart:95 | `String buildStoragePath(String companyId, Map<String, dynamic> localRecord)` | File adapters: construct storage path |
| extractRecordName | table_adapter.dart:174 | `String extractRecordName(Map<String, dynamic> record)` | Deletion notification display names |
| registerSyncAdapters | sync_registry.dart:29 | `void registerSyncAdapters()` | Called during initialization |
| adapterFor | sync_registry.dart:91 | `TableAdapter adapterFor(String tableName)` | Lookup adapter by table name |
| dependencyOrder | sync_registry.dart:105 | `List<String> get dependencyOrder` | FK-ordered table name list |

## Imports

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
```
