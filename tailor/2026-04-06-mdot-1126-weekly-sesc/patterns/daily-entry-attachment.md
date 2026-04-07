# Pattern: Daily-Entry Form Attachment & Export Bundling

## How We Do It

`form_response.entry_id` is the authoritative link from a filled form to a daily entry. `ExportEntryUseCase` (domain layer) iterates every `FormResponse` for that entry via `FormResponseRepository.getResponsesForEntry(entryId)` and calls `ExportFormUseCase` for each, producing one PDF per form. Currently it stores only the **first** PDF path in the `EntryExport` row (GitHub Issue #127 tracks bundle merging). The 1126 spec requires the export to group IDR + all attached form PDFs + photos into a single folder on disk — which is a behavior change to this use case.

## Exemplar: `ExportEntryUseCase.call` (export_entry_use_case.dart:16)

```dart
Future<List<String>> call(String entryId, {String? currentUserId}) async {
  final entry = await _entryRepository.getById(entryId);
  if (entry == null) return [];

  final responsesResult =
      await _formResponseRepository.getResponsesForEntry(entryId);
  final responses =
      responsesResult.isSuccess ? (responsesResult.data ?? []) : [];

  final paths = <String>[];
  for (final response in responses) {
    final path = await _exportFormUseCase.call(
      response.id,
      currentUserId: currentUserId,
    );
    if (path != null) paths.add(path);
  }

  // WHY: Without a metadata row, the sync engine has nothing to push.
  if (paths.isNotEmpty) {
    final savedFilePath = paths.first;   // <-- only first PDF recorded today
    final generatedFilename =
        'entry_report_${entryId.substring(0, 8)}.pdf';
    final export = EntryExport(
      entryId: entry.id,
      projectId: entry.projectId,
      filePath: savedFilePath,
      filename: generatedFilename,
      fileSizeBytes: await File(savedFilePath).length(),
      exportedAt: DateTime.now().toUtc().toIso8601String(),
      createdByUserId: currentUserId,
    );
    await _entryExportRepository.create(export);
    await _exportArtifactRepository.create(
      ExportArtifact(
        projectId: entry.projectId,
        artifactType: 'entry_pdf',
        sourceRecordId: entry.id,
        title: generatedFilename,
        filename: generatedFilename,
        localPath: savedFilePath,
        mimeType: 'application/pdf',
        createdByUserId: currentUserId,
      ),
    );
  }

  return paths;
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|---|---|---|---|
| `FormResponseRepository.getResponsesForEntry` | `form_response_repository.dart:14` | `Future<RepositoryResult<List<FormResponse>>> getResponsesForEntry(String entryId)` | All forms attached to an entry |
| `DailyEntryRepository.getByDate` | `daily_entry_repository.dart:9` | `Future<List<DailyEntry>> getByDate(String projectId, DateTime date)` | Resolve attach-default entry from `inspection_date` |
| `DailyEntryRepository.create` | `daily_entry_repository.dart:84` | `Future<RepositoryResult<DailyEntry>> create(DailyEntry entry)` | Inline create when no entry exists |
| `FormResponse.copyWith(entryId: X)` | `form_response.dart:121` | copyWith | Set attachment link |
| `FormResponse.withResponseDataPatch({...})` | `form_response.dart:334` | JSON merge | Update signature_audit_id in response payload |

## 1126 Application

### Resolve1126AttachmentEntryUseCase

```dart
class Resolve1126AttachmentEntryUseCase {
  final DailyEntryRepository _entryRepository;
  final CreateInspectionDateEntryUseCase _createEntryUseCase;

  Resolve1126AttachmentEntryUseCase(this._entryRepository, this._createEntryUseCase);

  /// Returns the existing entry matching inspection_date, or null if one must
  /// be created (caller prompts user then calls [createEntry]).
  Future<DailyEntry?> findDefault({
    required String projectId,
    required DateTime inspectionDate,
  }) async {
    final matches = await _entryRepository.getByDate(projectId, inspectionDate);
    return matches.isEmpty ? null : matches.first;
  }

  Future<DailyEntry> createEntry({
    required String projectId,
    required DateTime inspectionDate,
    required String currentUserId,
  }) => _createEntryUseCase.call(
        projectId: projectId,
        date: inspectionDate,
        currentUserId: currentUserId,
      );
}
```

### ExportEntryUseCase — one-folder bundling change

Rewrite the bundle step to:
1. Resolve a per-entry folder: `<docsDir>/exports/<projectId>/<entryDate>_<entryIdShort>/`
2. Move/copy IDR PDF, all form PDFs, and photo files into that folder
3. Record ONE `EntryExport` row whose `filePath` is the folder path (or zip path, TBD)
4. Record one `ExportArtifact` per file for downstream listing

Spec says: "IDR + 1126 + photos present in one folder" — plan must decide folder vs zip.

## Imports

```dart
import 'package:construction_inspector/features/entries/domain/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/features/forms/domain/repositories/form_response_repository.dart';
```
