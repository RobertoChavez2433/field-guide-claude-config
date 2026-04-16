# Pattern — PDF AcroForm Inspection Helper

Spec § PDF AcroForm Inspection Helper asked for research first. Research result: **the capability already exists in-repo via `syncfusion_flutter_pdf`**. No new dependency is required.

## Exemplars (in-repo, already running)

- `lib/features/forms/data/services/form_pdf_field_writer.dart:18-52` — enumerates `form.fields[i]`, matches by `field.name`, writes into `PdfTextBoxField` (including read-only fields) via syncfusion internal helpers.
- `lib/features/forms/data/services/form_pdf_rendering_service.dart:24-53` — `PdfDocument(inputBytes: templateBytes)` open → fill → save → dispose lifecycle.
- `test/features/forms/services/form_pdf_field_writer_test.dart:17-81` — round-trips a template through open → set → save → reopen, asserts `field.text`, asserts raw `/V` value.

## Minimum helper API (writer to finalize)

```dart
/// Inspects AcroForm fields in a PDF byte buffer for test assertions.
class PdfAcroFormInspector {
  PdfAcroFormInspector(Uint8List pdfBytes) : _doc = PdfDocument(inputBytes: pdfBytes);
  void dispose() => _doc.dispose();

  /// Iterates every AcroForm field name → value. Non-text field subclasses
  /// (`PdfLoadedCheckBoxField`, `PdfLoadedComboBoxField`, `PdfLoadedListBoxField`,
  /// `PdfLoadedRadioButtonListField`) expose their own value getters.
  Map<String, String?> readAllFieldValues();

  /// Returns true when the document still carries an AcroForm dictionary and
  /// `form.fields.count > 0` — false means the PDF was flattened.
  bool get hasEditableAcroForm;

  /// Returns field names that exist but whose value is null/empty.
  List<String> findUnpopulatedFields(List<String> expectedNames);

  final PdfDocument _doc;
}
```

## Rules

1. **Lives in test scope.** Suggested path `lib/shared/testing/pdf_acroform_inspector.dart` (reachable by both `test/` and by driver-mode export verifiers) or `test/support/pdf_acroform_inspector.dart` if the writer decides to keep it out of production import graph.
2. **Dispose the `PdfDocument`.** Existing code always calls `.dispose()` in a `finally` — keep that shape.
3. **Do not reach into syncfusion `src/pdf/implementation/…` unless necessary.** `FormPdfFieldWriter` already uses internal imports (`ignore_for_file: implementation_imports`) to persist values into read-only fields; read-only *inspection* does not need those — `field.text` and field-subtype downcasts are public API.
4. **Byte-compare fallback.** For flattened PDFs (no AcroForm left), the spec allows a canonical golden PDF per form type. Put fixtures under `test/fixtures/pdf/golden_<form_type>.pdf`; compare `crypto.sha256` over the bytes. Flag false positives — a new PDF build often reorders object streams even without content change, so byte-compare is a last resort.
5. **No license change.** `syncfusion_flutter_pdf` is already in `pubspec.yaml` at version `^32.1.25` and is already used in production exports (`FormPdfRenderingService.generateFormPdf`), so the spec's "commercial license concern" is already accepted for the product.

## Consumption

The `form_completeness` and `export_verification` sub-flows call this helper after hitting `POST /driver/tap` on the export button and reading back the exported bytes (existing export code paths save via `ShareService` / file system). The helper asserts `hasEditableAcroForm` and `findUnpopulatedFields([...])` is empty.
