# Pattern: Builtin Form Registration

## How We Do It

Every builtin MDOT form is declared as a single `BuiltinFormConfig` entry inside the `builtinForms` const list in `lib/features/forms/data/registries/builtin_forms.dart`. Each config points to a one-shot `register<FormName>()` function that registers the form's capabilities (validator, initial data, PDF filler, calculator, quick actions) with the matching registry singletons. This keeps every form's "contract" in one discoverable place and lets the repository seed inspector_form rows via `BuiltinFormConfig.toInspectorForm()`.

## Exemplars

### `builtinForms` (builtin_forms.dart)

```dart
final builtinForms = List.unmodifiable([
  const BuiltinFormConfig(
    id: 'mdot_0582b',
    name: 'MDOT 0582B Density',
    templatePath: 'assets/templates/forms/mdot_0582b_form.pdf',
    registerCapabilities: registerMdot0582B,
  ),
  // NOTE: Future forms added here.
]);
```

### `BuiltinFormConfig` (builtin_form_config.dart)

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

### `registerMdot0582B()` (mdot_0582b_registrations.dart)

```dart
void registerMdot0582B() {
  FormCalculatorRegistry.instance.register('mdot_0582b', Mdot0582BFormCalculator());

  FormValidatorRegistry.instance.register('mdot_0582b', validateMdot0582B);

  FormInitialDataFactory.instance.register('mdot_0582b', () {
    return {
      'test_rows': [calc.Mdot0582BCalculator.emptyTestRow()],
      'proctor_rows': [calc.Mdot0582BCalculator.emptyProctorRow()],
    };
  });

  FormPdfFillerRegistry.instance.register('mdot_0582b', fillMdot0582bPdfFields);

  // NOTE: FormScreenRegistry registration for 0582B is deferred to the UI layer.
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|---|---|---|---|
| `FormValidatorRegistry.instance.register` | `form_validator_registry.dart:16` | `void register(String formId, FormValidator validator)` | Register per-form validation function |
| `FormInitialDataFactory.instance.register` | `form_initial_data_factory.dart:15` | `void register(String formId, InitialDataBuilder builder)` | Provide structured default `response_data` |
| `FormPdfFillerRegistry.instance.register` | `form_pdf_filler_registry.dart:19` | `void register(String formId, PdfFieldFiller filler)` | Map `(responseData, headerData) → PDF field map` |
| `FormScreenRegistry.instance.register` | `form_screen_registry.dart:21` | `void register(String formId, FormScreenBuilder builder)` | Bind form-specific screen (deferred to UI init) |
| `FormQuickActionRegistry.instance.register` | `form_quick_action_registry.dart:76` | `void register(String formId, List<FormQuickAction> actions)` | Add "New 1126" hub quick action |
| `BuiltinFormConfig.toInspectorForm` | `builtin_form_config.dart:17` | `InspectorForm toInspectorForm()` | Seeds repository with builtin row |

## 1126 Application

```dart
// lib/features/forms/data/registries/mdot_1126_registrations.dart
void registerMdot1126() {
  // No calculator — 1126 has no numeric calcs.

  FormValidatorRegistry.instance.register(kFormTypeMdot1126, validateMdot1126);

  FormInitialDataFactory.instance.register(kFormTypeMdot1126, () {
    return {
      'rainfall_events': <Map<String, dynamic>>[],
      'measures': <Map<String, dynamic>>[],
      'signature_audit_id': null,
    };
  });

  FormPdfFillerRegistry.instance.register(kFormTypeMdot1126, fillMdot1126PdfFields);

  FormQuickActionRegistry.instance.register(kFormTypeMdot1126, [
    FormQuickAction(
      icon: Icons.rainy_heavy,  // via IconsX / design system
      label: 'New 1126',
      execute: () => const FormQuickActionResult.navigate(
        name: 'form-new',
        pathParams: {'formId': kFormTypeMdot1126},
      ),
    ),
  ]);
}
```

And append to `builtinForms`:

```dart
const BuiltinFormConfig(
  id: kFormTypeMdot1126,                      // 'mdot_1126'
  name: 'MDOT 1126 Weekly SESC',
  templatePath: kFormTemplateMdot1126,         // 'assets/templates/forms/mdot_1126_form.pdf'
  registerCapabilities: registerMdot1126,
),
```

## Imports

```dart
import 'package:construction_inspector/features/forms/data/registries/builtin_form_config.dart';
import 'package:construction_inspector/features/forms/data/registries/form_type_constants.dart';
import 'package:construction_inspector/features/forms/data/registries/form_validator_registry.dart';
import 'package:construction_inspector/features/forms/data/registries/form_initial_data_factory.dart';
import 'package:construction_inspector/features/forms/data/registries/form_pdf_filler_registry.dart';
import 'package:construction_inspector/features/forms/data/registries/form_quick_action_registry.dart';
import 'package:construction_inspector/features/forms/data/validators/mdot_1126_validator.dart';
import 'package:construction_inspector/features/forms/data/pdf/mdot_1126_pdf_filler.dart';
```
