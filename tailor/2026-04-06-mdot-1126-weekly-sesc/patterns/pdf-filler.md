# Pattern: PDF Field Filler

## How We Do It

Each form exports a free-standing `fillMdot<code>PdfFields(responseData, headerData)` pure function that returns a `Map<String,String>` of PDF AcroForm field name → value. The function is registered with `FormPdfFillerRegistry` keyed by form type. `FormPdfService.generateFormPdf` looks up the filler, applies it to flatten-fill the template, and returns bytes. A local helper `putValue(key, value)` skips empty strings so that unset fields never clobber template defaults.

## Exemplar: `fillMdot0582bPdfFields` (mdot_0582b_pdf_filler.dart)

```dart
Map<String, String> fillMdot0582bPdfFields(
    Map<String, dynamic> responseData, Map<String, dynamic> headerData) {
  final mapped = <String, String>{};

  void putValue(String key, dynamic value) {
    final text = value?.toString().trim() ?? '';
    if (text.isEmpty) return;
    mapped[key] = text;
  }

  // Header fields
  putValue('date', headerData['date']);
  putValue('control_section_id', headerData['control_section_id']);
  putValue('job_number', headerData['job_number'] ?? headerData['project_number']);
  putValue('route_street', headerData['route_street']);
  // ...

  // Row-indexed fields: iterate a list, build PDF keys like '1Row1', '2Row1'
  final testRowsRaw = responseData['test_rows'];
  final testRows = testRowsRaw is List
      ? testRowsRaw.whereType<Map>().map((r) => r.cast<String, dynamic>()).toList()
      : <Map<String, dynamic>>[];
  for (var i = 0; i < testRows.length; i++) {
    final rowNum = i + 1;
    final row = testRows[i];
    putValue('1Row$rowNum', row['is_recheck'] == true ? 'R' : 'O');
    // ...
  }

  putValue('remarks', responseData['remarks']);

  return mapped;
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|---|---|---|---|
| `FormPdfFillerRegistry.instance.register` | `form_pdf_filler_registry.dart:19` | `void register(String formId, PdfFieldFiller filler)` | Hook into service |
| `FormPdfFillerRegistry.instance.get` | `form_pdf_filler_registry.dart:28` | `PdfFieldFiller? get(String formId)` | Service lookup during fill |
| `FormPdfService.generateFilledPdf` | `form_pdf_service.dart:1126` | `Future<Uint8List?> generateFilledPdf(FormResponse response)` | End-to-end flatten-fill |

## 1126 Application

The 1126 AcroForm (see `.claude/specs/assets/mdot-1126-weekly-sesc.pdf`) has:
- Header block: project, contractor, inspector, permit #, location, report #, inspection_date, date_of_last_inspection
- Rainfall grid: N rows of (date, inches) — field names to be discovered during PDF introspection
- Measures grid: description, location, status (in place / needs action / removed), corrective action
- Signature image field (embedded raster, handled outside the filler — the filler just emits the inspector name)

```dart
Map<String, String> fillMdot1126PdfFields(
    Map<String, dynamic> responseData, Map<String, dynamic> headerData) {
  final mapped = <String, String>{};
  void putValue(String key, dynamic value) {
    final text = value?.toString().trim() ?? '';
    if (text.isEmpty) return;
    mapped[key] = text;
  }

  // Header
  putValue('project', headerData['project_number'] ?? headerData['job_number']);
  putValue('contractor', headerData['contractor']);
  putValue('inspector', headerData['inspector']);
  putValue('permit_number', headerData['permit_number']);
  putValue('location', headerData['location']);
  putValue('report_number', responseData['report_number']);
  putValue('inspection_date', responseData['inspection_date']);
  putValue('date_of_last_inspection', responseData['date_of_last_inspection']);

  // Rainfall
  final rainfall = (responseData['rainfall_events'] as List? ?? [])
      .whereType<Map>()
      .map((r) => r.cast<String, dynamic>())
      .toList();
  for (var i = 0; i < rainfall.length; i++) {
    putValue('rainfall_date_${i + 1}', rainfall[i]['date']);
    putValue('rainfall_inches_${i + 1}', rainfall[i]['inches']);
  }

  // Measures
  final measures = (responseData['measures'] as List? ?? [])
      .whereType<Map>()
      .map((r) => r.cast<String, dynamic>())
      .toList();
  for (var i = 0; i < measures.length; i++) {
    final row = i + 1;
    final m = measures[i];
    putValue('measure_desc_$row', m['description']);
    putValue('measure_loc_$row', m['location']);
    putValue('measure_status_$row', _statusLabel(m['status']));
    putValue('measure_corrective_$row', m['corrective_action']);
  }

  return mapped;
}

String _statusLabel(dynamic status) => switch (status) {
      'in_place' => 'X',  // checkbox
      'needs_action' => 'X',
      'removed' => 'X',
      _ => '',
    };
```

> **Note**: actual AcroForm field names must be introspected from the template PDF via `FormPdfService.generateDebugPdf`. The plan must include a spike step to extract the real names before wiring them in.

## Imports

```dart
// mdot_1126_pdf_filler.dart is a pure function file — no Flutter imports.
// The service layer (form_pdf_service.dart) handles PDF library imports.
```

## Signature Image Embedding

Signature PNG bytes are **not** handled by this filler. The signing flow writes a PNG to disk (`signature_files.local_path`) and `FormPdfService` stamps it into the flattened PDF at a known coordinate. Follow the existing asset-stamping pattern in `FormPdfService` (lines near `generateFormPdf`) — likely a new `_embedSignaturePng` helper on the service that is called after the filler runs.
