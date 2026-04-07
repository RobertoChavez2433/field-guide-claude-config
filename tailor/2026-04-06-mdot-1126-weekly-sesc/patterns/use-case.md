# Pattern: Domain Use Case

## How We Do It

Use cases live in `lib/features/<feature>/domain/usecases/<name>_use_case.dart`. They are thin coordinators that wrap one or more repositories, expose a single `call()` (or named method) that returns a `Future<RepositoryResult<T>>` or a plain `Future<T>`. They do not depend on Flutter, Supabase, or sqflite directly — only on the abstract `*Repository` interfaces. Providers (`ChangeNotifier`) construct the use case with injected repositories and call it from the presentation layer.

## Exemplar — `ExportEntryUseCase` constructor shape

```dart
class ExportEntryUseCase {
  final DailyEntryRepository _entryRepository;
  final EntryExportRepository _entryExportRepository;
  final FormResponseRepository _formResponseRepository;
  final ExportFormUseCase _exportFormUseCase;
  final ExportArtifactRepository _exportArtifactRepository;

  ExportEntryUseCase({
    required DailyEntryRepository entryRepository,
    required EntryExportRepository entryExportRepository,
    required FormResponseRepository formResponseRepository,
    required ExportFormUseCase exportFormUseCase,
    required ExportArtifactRepository exportArtifactRepository,
  })  : _entryRepository = entryRepository,
        _entryExportRepository = entryExportRepository,
        _formResponseRepository = formResponseRepository,
        _exportFormUseCase = exportFormUseCase,
        _exportArtifactRepository = exportArtifactRepository;

  Future<List<String>> call(String entryId, {String? currentUserId}) async { ... }
}
```

## 1126 Use Cases

### LoadPrior1126UseCase

```dart
class LoadPrior1126UseCase {
  final FormResponseRepository _repo;
  LoadPrior1126UseCase(this._repo);

  Future<FormResponse?> call({required String projectId}) async {
    // Requires new repo method getByFormTypeForProject(projectId, formType, {limit, orderBy})
    final result = await _repo.getByFormTypeForProject(
      projectId: projectId,
      formType: kFormTypeMdot1126,
      orderByResponseField: 'inspection_date',
      descending: true,
      limit: 1,
    );
    return result.isSuccess && (result.data ?? []).isNotEmpty ? result.data!.first : null;
  }
}
```

> **NOTE**: `FormResponseRepository` does not currently expose this query. Plan must add `getByFormTypeForProject` to the abstract repo + local datasource.

### BuildCarryForward1126UseCase

```dart
class BuildCarryForward1126UseCase {
  Map<String, dynamic> call({
    required FormResponse prior,
    required DateTime newInspectionDate,
  }) {
    final priorResponse = prior.parsedResponseData;
    final priorHeader = prior.parsedHeaderData;
    final priorMeasures = (priorResponse['measures'] as List? ?? [])
        .whereType<Map>()
        .map((m) => m.cast<String, dynamic>())
        .toList();

    // Carry over measures with status reset to in_place and corrective_action cleared
    final carriedMeasures = priorMeasures.map((m) => {
      'id': m['id'],
      'description': m['description'],
      'location': m['location'],
      'status': 'in_place',
      'corrective_action': '',
    }).toList();

    final priorReportNum = int.tryParse(priorResponse['report_number']?.toString() ?? '') ?? 0;

    return {
      'header': priorHeader,  // carried verbatim
      'report_number': (priorReportNum + 1).toString(),
      'inspection_date': _iso(newInspectionDate),
      'date_of_last_inspection': priorResponse['inspection_date'],
      'rainfall_events': <Map<String, dynamic>>[],
      'measures': carriedMeasures,
      'signature_audit_id': null,
      'weekly_cycle_anchor_date': priorResponse['weekly_cycle_anchor_date'],
    };
  }

  String _iso(DateTime d) => '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';
}
```

### SignFormResponseUseCase (generic — not 1126-specific)

```dart
class SignFormResponseUseCase {
  final SignatureFileRepository _fileRepo;
  final SignatureAuditLogRepository _auditRepo;
  final FormResponseRepository _formRepo;
  final DeviceInfoService _deviceInfo;
  final LocationService _location;
  final AuthSession _session;
  final Directory _appDocs;

  SignFormResponseUseCase(...);

  Future<String> call({
    required String formResponseId,
    required Uint8List signaturePngBytes,
    required Uint8List preSignPdfBytes,
  }) async {
    final fileId = _uuid();
    final path = '${_appDocs.path}/signatures/$fileId.png';
    await File(path).writeAsBytes(signaturePngBytes);

    final pngSha = sha256.convert(signaturePngBytes).toString();
    final pdfSha = sha256.convert(preSignPdfBytes).toString();

    final file = SignatureFile(
      id: fileId,
      projectId: _session.projectId,
      companyId: _session.companyId,
      localPath: path,
      mimeType: 'image/png',
      fileSizeBytes: signaturePngBytes.length,
      sha256: pngSha,
      createdByUserId: _session.userId,
    );
    await _fileRepo.create(file);

    final auditId = _uuid();
    final audit = SignatureAuditLog(
      id: auditId,
      signedRecordType: 'form_response',
      signedRecordId: formResponseId,
      projectId: _session.projectId,
      companyId: _session.companyId,
      userId: _session.userId,
      deviceId: await _deviceInfo.id(),
      platform: _deviceInfo.platform,
      appVersion: _deviceInfo.appVersion,
      signedAtUtc: DateTime.now().toUtc().toIso8601String(),
      gpsLat: await _location.maybeLatitude(),
      gpsLng: await _location.maybeLongitude(),
      documentHashSha256: pdfSha,
      signatureFileId: fileId,
    );
    await _auditRepo.create(audit);

    // Stamp the audit id into the form_response payload
    final response = await _formRepo.getById(formResponseId);
    if (response != null) {
      final patched = response.withResponseDataPatch({
        'signature_audit_id': auditId,
      });
      await _formRepo.update(patched);
    }
    return auditId;
  }
}
```

### InvalidateFormSignatureOnEditUseCase

```dart
class InvalidateFormSignatureOnEditUseCase {
  final FormResponseRepository _formRepo;
  InvalidateFormSignatureOnEditUseCase(this._formRepo);

  Future<void> call(String formResponseId) async {
    final response = await _formRepo.getById(formResponseId);
    if (response == null) return;
    final current = response.parsedResponseData['signature_audit_id'];
    if (current == null) return;  // nothing to clear
    final patched = response.withResponseDataPatch({'signature_audit_id': null});
    await _formRepo.update(patched);
  }
}
```

### ComputeWeeklySescReminderUseCase

```dart
class ComputeWeeklySescReminderUseCase {
  final FormResponseRepository _formRepo;
  final ProjectRepository _projectRepo;

  ComputeWeeklySescReminderUseCase(this._formRepo, this._projectRepo);

  /// Returns null if no reminder should fire.
  Future<WeeklySescReminder?> call({
    required String projectId,
    required DateTime today,
  }) async {
    final project = await _projectRepo.getById(projectId);
    if (project == null || !project.isActive || project.deletedAt != null) return null;

    final result = await _formRepo.getByFormTypeForProject(
      projectId: projectId,
      formType: kFormTypeMdot1126,
      descending: false,  // ascending — need the first signed one for anchor
    );
    final all = result.data ?? [];

    // Only consider signed ones for anchoring
    final signed = all.where((r) {
      final json = r.parsedResponseData;
      return json['signature_audit_id'] != null;
    }).toList();
    if (signed.isEmpty) return null;

    final anchor = DateTime.parse(signed.first.parsedResponseData['inspection_date']);
    final daysSinceAnchor = today.difference(anchor).inDays;
    final cycleIndex = daysSinceAnchor ~/ 7;
    final currentDueDate = anchor.add(Duration(days: (cycleIndex + 1) * 7));

    // Has this cycle been satisfied?
    final cycleStart = anchor.add(Duration(days: cycleIndex * 7));
    final hasFillThisCycle = signed.any((r) {
      final d = DateTime.parse(r.parsedResponseData['inspection_date']);
      return !d.isBefore(cycleStart) && d.isBefore(currentDueDate);
    });

    if (hasFillThisCycle) return null;

    return WeeklySescReminder(
      anchorDate: anchor,
      currentDueDate: currentDueDate,
      daysOverdue: today.isAfter(currentDueDate)
          ? today.difference(currentDueDate).inDays
          : 0,
    );
  }
}
```

## Reusable Methods

Existing use-case DI binding happens in `lib/core/di/` — plan must wire new use cases into the container following existing pattern.

## Imports

```dart
import 'package:construction_inspector/features/forms/domain/repositories/form_response_repository.dart';
import 'package:construction_inspector/features/forms/data/registries/form_type_constants.dart';
import 'package:crypto/crypto.dart';
```
