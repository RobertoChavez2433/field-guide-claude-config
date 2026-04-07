# Pattern: Form Validator

## How We Do It

Each form exports a free-standing `validateMdot<code>(responseData, headerData)` pure function returning a `List<String>` of missing-field labels (empty list = valid). The function lives under `lib/features/forms/data/validators/` and is registered with `FormValidatorRegistry` keyed by form type. A context flag `__for_export__ = true` can be set in `headerData` to tighten the rules at export time (e.g. block PDFs with missing sig). `FormValidatorRegistry.validate()` returns empty list if no validator is registered.

## Exemplar: `validateMdot0582B` (mdot_0582b_validator.dart)

```dart
List<String> validateMdot0582B(
    Map<String, dynamic> responseData, Map<String, dynamic> headerData) {
  final forExport = headerData['__for_export__'] == true;
  final missing = <String>[];

  bool hasValue(Map<String, dynamic> map, String key) {
    final value = map[key];
    return value != null && value.toString().trim().isNotEmpty;
  }

  void requireHeader(String key, String label) {
    if (!hasValue(headerData, key)) missing.add(label);
  }

  requireHeader('date', 'date');
  requireHeader('job_number', 'job_number');
  requireHeader('inspector', 'inspector');

  if (forExport) {
    requireHeader('control_section_id', 'control_section_id');
    // ...
  }

  final proctors = responseData['proctor_rows'];
  if (proctors is! List || proctors.isEmpty) missing.add('proctor_rows');
  // ...

  return missing;
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|---|---|---|---|
| `FormValidatorRegistry.instance.register` | `form_validator_registry.dart:16` | `void register(String formId, FormValidator validator)` | Hook into repository |
| `FormValidatorRegistry.instance.validate` | `form_validator_registry.dart:28` | `List<String> validate(formId, responseData, headerData)` | Safe call — returns `[]` if no validator |

## 1126 Application

```dart
// lib/features/forms/data/validators/mdot_1126_validator.dart
List<String> validateMdot1126(
    Map<String, dynamic> responseData, Map<String, dynamic> headerData) {
  final forExport = headerData['__for_export__'] == true;
  final missing = <String>[];

  bool has(Map<String, dynamic> m, String k) {
    final v = m[k];
    return v != null && v.toString().trim().isNotEmpty;
  }

  void requireResponse(String k, String label) {
    if (!has(responseData, k)) missing.add(label);
  }

  requireResponse('inspection_date', 'inspection_date');

  // All measures must be resolved to a tri-state
  final measures = (responseData['measures'] as List? ?? [])
      .whereType<Map>()
      .map((r) => r.cast<String, dynamic>())
      .toList();
  for (var i = 0; i < measures.length; i++) {
    final status = measures[i]['status']?.toString() ?? '';
    if (!{'in_place', 'needs_action', 'removed'}.contains(status)) {
      missing.add('measure_status_${i + 1}');
    }
    if (status == 'needs_action' &&
        !has(measures[i].cast<String, dynamic>(), 'corrective_action')) {
      missing.add('measure_corrective_${i + 1}');
    }
  }

  // Signature: active audit id must be present
  if (!has(responseData, 'signature_audit_id')) {
    missing.add('signature');
  }

  if (forExport) {
    // Block export while unsigned or re-sign is pending.
    if (!has(responseData, 'signature_audit_id')) {
      missing.add('signature(required for export)');
    }
  }

  return missing;
}
```

## Imports

```dart
// Pure function, no imports beyond Dart core.
```
