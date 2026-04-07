# Source Excerpts — By File

Full source of the exemplar symbols that the writing-plans step should copy-paste from.

## lib/features/forms/data/registries/builtin_forms.dart

```dart
final builtinForms = List.unmodifiable([
  const BuiltinFormConfig(
    id: 'mdot_0582b',
    name: 'MDOT 0582B Density',
    templatePath: 'assets/templates/forms/mdot_0582b_form.pdf',
    registerCapabilities: registerMdot0582B,
  ),
  // NOTE: Future forms added here. Example:
  // BuiltinFormConfig(
  //   id: 'mdot_1120',
  //   name: 'MDOT 1120 Concrete',
  //   templatePath: FormPdfService.mdot1120TemplatePath,
  //   registerCapabilities: registerMdot1120,
  // ),
]);
```

## lib/features/forms/data/registries/builtin_form_config.dart

```dart
class BuiltinFormConfig {
  final String id;
  final String name;
  final String templatePath;
  final void Function() registerCapabilities;

  const BuiltinFormConfig({
    required this.id,
    required this.name,
    required this.templatePath,
    required this.registerCapabilities,
  });

  InspectorForm toInspectorForm() => InspectorForm(
        id: id,
        name: name,
        templatePath: templatePath,
        isBuiltin: true,
        projectId: null,
      );
}
```

## lib/features/forms/data/registries/mdot_0582b_registrations.dart::registerMdot0582B

See `patterns/builtin-form-registration.md`. Used as the one-shot registration entry point.

## lib/features/forms/data/pdf/mdot_0582b_pdf_filler.dart::fillMdot0582bPdfFields

See `patterns/pdf-filler.md`. The exemplar for `fillMdot1126PdfFields`.

## lib/features/forms/data/validators/mdot_0582b_validator.dart::validateMdot0582B

See `patterns/validator.md`. The exemplar for `validateMdot1126`.

## lib/features/forms/data/registries/form_type_constants.dart (current)

```dart
// Existing
const String kFormTypeMdot0582b = 'mdot_0582b';
const String kFormTemplateMdot0582b = 'assets/templates/forms/mdot_0582b_form.pdf';
```

Spec addition (verified location):

```dart
const String kFormTypeMdot1126 = 'mdot_1126';
const String kFormTemplateMdot1126 = 'assets/templates/forms/mdot_1126_form.pdf';
```

## lib/features/forms/data/registries/form_screen_registry.dart

```dart
typedef FormScreenBuilder = Widget Function({
  required String formId,
  required String responseId,
  required String projectId,
});

class FormScreenRegistry {
  FormScreenRegistry._();
  static final instance = FormScreenRegistry._();
  final _builders = <String, FormScreenBuilder>{};

  void register(String formId, FormScreenBuilder builder) {
    _builders.putIfAbsent(formId, () => builder);
  }
  FormScreenBuilder? get(String formId) => _builders[formId];
  bool hasCustomScreen(String formId) => _builders.containsKey(formId);
  void clear() => _builders.clear();
}
```

## lib/features/forms/data/registries/form_pdf_filler_registry.dart

```dart
typedef PdfFieldFiller = Map<String, String> Function(
  Map<String, dynamic> responseData,
  Map<String, dynamic> headerData,
);

class FormPdfFillerRegistry {
  FormPdfFillerRegistry._();
  static final instance = FormPdfFillerRegistry._();
  final _fillers = <String, PdfFieldFiller>{};

  void register(String formId, PdfFieldFiller filler) {
    _fillers.putIfAbsent(formId, () => filler);
  }
  PdfFieldFiller? get(String formId) => _fillers[formId];
  bool hasFiller(String formId) => _fillers.containsKey(formId);
  void clear() => _fillers.clear();
}
```

## lib/features/forms/data/registries/form_validator_registry.dart

```dart
typedef FormValidator = List<String> Function(
    Map<String, dynamic> responseData, Map<String, dynamic> headerData);

class FormValidatorRegistry {
  FormValidatorRegistry._();
  static final instance = FormValidatorRegistry._();
  final _validators = <String, FormValidator>{};

  void register(String formId, FormValidator validator) {
    _validators.putIfAbsent(formId, () => validator);
  }
  FormValidator? get(String formId) => _validators[formId];
  List<String> validate(String formId, Map<String, dynamic> responseData,
      Map<String, dynamic> headerData) {
    final v = _validators[formId];
    if (v == null) return const [];
    return v(responseData, headerData);
  }
  void clear() => _validators.clear();
}
```

## lib/features/forms/data/registries/form_initial_data_factory.dart

```dart
typedef InitialDataBuilder = Map<String, dynamic> Function();

class FormInitialDataFactory {
  FormInitialDataFactory._();
  static final instance = FormInitialDataFactory._();
  final _builders = <String, InitialDataBuilder>{};

  void register(String formId, InitialDataBuilder builder) {
    _builders.putIfAbsent(formId, () => builder);
  }
  Map<String, dynamic>? buildInitialData(String formId) =>
      _builders[formId]?.call();
}
```

## lib/core/database/schema/support_tables.dart

See `patterns/schema-table.md` — full source inlined.

## lib/features/sync/adapters/adapter_config.dart::AdapterConfig

See `patterns/sync-adapter-config.md`.

## lib/features/sync/adapters/simple_adapters.dart — relevant exemplars

See `patterns/sync-adapter-config.md` (entry_contractors standard, form_exports file-backed).

## lib/features/entries/domain/usecases/export_entry_use_case.dart::ExportEntryUseCase

See `patterns/daily-entry-attachment.md`.

## lib/features/forms/data/models/form_response.dart — key APIs

```dart
// Relevant for 1126:
String? entryId;
FormResponse copyWith({Object? entryId = _sentinel, Object? responseData = _sentinel, ... });
Map<String, dynamic> get parsedHeaderData;
Map<String, dynamic> get parsedResponseData;
FormResponse withResponseDataPatch(Map<String, dynamic> patch);
```

## lib/core/database/database_service.dart — schema version anchors

```dart
// Line 69 and 110 — both declare version: 53 and must be bumped in lockstep.
version: 53,
```

## lib/features/forms/presentation/providers/inspector_form_provider.dart

Constructor — existing dependencies the 1126 flow reuses:

```dart
InspectorFormProvider({
  required LoadFormsUseCase loadFormsUseCase,
  required LoadFormResponsesUseCase loadFormResponsesUseCase,
  required SaveFormResponseUseCase saveFormResponseUseCase,
  required SubmitFormResponseUseCase submitFormResponseUseCase,
  required DeleteFormResponseUseCase deleteFormResponseUseCase,
  required CalculateFormFieldUseCase calculateFormFieldUseCase,
  required this.canWrite,
});
```

Plan must add the new 1126 use cases either as constructor params on this provider OR a new `Weekly1126Provider` that wraps `InspectorFormProvider`. Spec says "reuses existing InspectorFormProvider" → prefer extension methods in `inspector_form_provider_response_actions.dart` for the simple actions, and a new thin `Weekly1126Controller` for the guided-flow state (matches "sync-observable controller" pattern per CLAUDE.md).
