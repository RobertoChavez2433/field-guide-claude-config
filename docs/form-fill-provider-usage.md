# FormFillProvider Usage Guide

## Overview

`FormFillProvider` manages form fill state and auto-fill operations for a single form response. It tracks field values, auto-fill results, and user edits.

## Architecture

```
Global Provider Tree (main.dart):
├── AutoFillEngine             # Singleton service - no state
├── AutoFillContextBuilder     # Singleton service - no state
├── InspectorFormRepository    # Available for dependency injection
├── FormResponseRepository     # Available for dependency injection
└── FormFieldRegistryRepository # Available for dependency injection

Per-Screen Provider (created on-demand):
└── FormFillProvider           # Per-form state management
```

## Wiring in main.dart

The following services are now globally available (as of Phase 5):

```dart
// In main.dart
final autoFillEngine = AutoFillEngine();
final autoFillContextBuilder = AutoFillContextBuilder();

MultiProvider(
  providers: [
    // ... other providers ...
    Provider<AutoFillEngine>.value(value: autoFillEngine),
    Provider<AutoFillContextBuilder>.value(value: autoFillContextBuilder),
    Provider<InspectorFormRepository>.value(...),
    Provider<FormResponseRepository>.value(...),
    Provider<FormFieldRegistryRepository>.value(...),
  ],
)
```

## Usage Pattern: Per-Screen Provider

`FormFillProvider` should be instantiated per-screen, not globally, since it manages state for a single form response.

### Example: Form Fill Screen

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/features/toolbox/data/repositories/repositories.dart';
import 'package:construction_inspector/features/toolbox/presentation/providers/form_fill_provider.dart';
import 'package:construction_inspector/features/toolbox/data/services/services.dart';

class FormFillScreen extends StatelessWidget {
  final String formId;
  final String? responseId; // For editing existing responses
  final String projectId;
  final String entryId;

  const FormFillScreen({
    super.key,
    required this.formId,
    this.responseId,
    required this.projectId,
    required this.entryId,
  });

  @override
  Widget build(BuildContext context) {
    // Create FormFillProvider for this screen
    return ChangeNotifierProvider(
      create: (context) {
        final provider = FormFillProvider(
          context.read<InspectorFormRepository>(),
          context.read<FormResponseRepository>(),
          context.read<FormFieldRegistryRepository>(),
          context.read<AutoFillEngine>(),
        );

        // Load form data
        provider.loadForm(formId: formId, responseId: responseId);

        return provider;
      },
      child: _FormFillScreenContent(
        projectId: projectId,
        entryId: entryId,
      ),
    );
  }
}

class _FormFillScreenContent extends StatelessWidget {
  final String projectId;
  final String entryId;

  const _FormFillScreenContent({
    required this.projectId,
    required this.entryId,
  });

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<FormFillProvider>();

    if (provider.isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (provider.error != null) {
      return Scaffold(
        body: Center(child: Text('Error: ${provider.error}')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(provider.form?.title ?? 'Form'),
        actions: [
          // Auto-fill button
          IconButton(
            icon: const Icon(Icons.auto_fix_high),
            onPressed: () => _handleAutoFill(context),
          ),
          // Save button
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: () => _handleSave(context),
          ),
        ],
      ),
      body: _buildFormContent(context, provider),
    );
  }

  Widget _buildFormContent(BuildContext context, FormFillProvider provider) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Render form fields
        for (final field in provider.fields)
          Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: _buildFormField(context, provider, field),
          ),
      ],
    );
  }

  Widget _buildFormField(
    BuildContext context,
    FormFillProvider provider,
    FormFieldEntry field,
  ) {
    final value = provider.fieldValues[field.fieldName] ?? '';
    final isAutoFilled = provider.isFieldAutoFilled(field.fieldName);
    final isUserEdited = provider.isFieldUserEdited(field.fieldName);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Field label with auto-fill indicator
        Row(
          children: [
            Text(
              field.label ?? field.fieldName,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            if (isAutoFilled)
              const Padding(
                padding: EdgeInsets.only(left: 8),
                child: Icon(Icons.auto_fix_high, size: 16, color: Colors.blue),
              ),
            if (isUserEdited)
              const Padding(
                padding: EdgeInsets.only(left: 8),
                child: Icon(Icons.edit, size: 16, color: Colors.orange),
              ),
          ],
        ),
        const SizedBox(height: 8),
        // Text input
        TextFormField(
          initialValue: value,
          decoration: InputDecoration(
            hintText: field.placeholder,
            border: const OutlineInputBorder(),
            // Show auto-fill source
            helperText: isAutoFilled
                ? 'Auto-filled from ${provider.getAutoFillResult(field.fieldName)?.sourceDescription ?? "unknown"}'
                : null,
          ),
          onChanged: (newValue) {
            provider.setFieldValue(field.fieldName, newValue, markAsEdited: true);
          },
        ),
      ],
    );
  }

  Future<void> _handleAutoFill(BuildContext context) async {
    final provider = context.read<FormFillProvider>();
    final contextBuilder = context.read<AutoFillContextBuilder>();

    // Build auto-fill context
    final autoFillContext = await contextBuilder.buildContext(
      context: context,
      projectId: projectId,
      entryId: entryId,
    );

    // Run auto-fill
    await provider.autoFillAll(
      context: autoFillContext,
      forceOverwrite: false, // Don't overwrite user edits
    );

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Form auto-filled')),
      );
    }
  }

  Future<void> _handleSave(BuildContext context) async {
    final provider = context.read<FormFillProvider>();

    final success = await provider.saveResponse(
      projectId: projectId,
      entryId: entryId,
    );

    if (context.mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Form saved')),
        );
        Navigator.of(context).pop();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${provider.error}')),
        );
      }
    }
  }
}
```

## Key Methods

### Loading Form
```dart
await provider.loadForm(formId: 'form-123', responseId: 'response-456');
```

### Setting Field Values
```dart
// Mark as user-edited (prevents auto-fill overwrite)
provider.setFieldValue('inspector_name', 'John Doe', markAsEdited: true);

// Don't mark as edited (allows auto-fill to overwrite)
provider.setFieldValue('date', '2026-01-28', markAsEdited: false);
```

### Auto-Fill
```dart
// Build context
final context = await autoFillContextBuilder.buildContext(
  context: context,
  projectId: 'proj-123',
  entryId: 'entry-456',
);

// Auto-fill (respects user edits)
await provider.autoFillAll(context: context, forceOverwrite: false);

// Force overwrite all fields
await provider.autoFillAll(context: context, forceOverwrite: true);
```

### Saving
```dart
// Save draft
final success = await provider.saveResponse(
  projectId: 'proj-123',
  entryId: 'entry-456',
);

// Submit final
final success = await provider.submitResponse(
  projectId: 'proj-123',
  entryId: 'entry-456',
);
```

## State Management

### Field Value Tracking
```dart
final fieldValues = provider.fieldValues; // Map<String, String>
final value = provider.fieldValues['inspector_name'];
```

### Auto-Fill Results
```dart
final result = provider.getAutoFillResult('inspector_name');
if (result != null) {
  print('Value: ${result.value}');
  print('Source: ${result.source}');
  print('Confidence: ${result.confidence}');
  print('Description: ${result.sourceDescription}');
}
```

### User Edit Detection
```dart
final isAutoFilled = provider.isFieldAutoFilled('inspector_name');
final isUserEdited = provider.isFieldUserEdited('inspector_name');
```

## Best Practices

1. **Per-Screen Provider**: Always create `FormFillProvider` at the screen level, not globally.

2. **Load After Creation**: Call `loadForm()` immediately after creating the provider.

3. **Check Mounted**: Always check `context.mounted` after async operations.

4. **Mark User Edits**: Set `markAsEdited: true` when user manually changes a field.

5. **Force Overwrite Carefully**: Only use `forceOverwrite: true` when explicitly requested by user.

6. **Show Auto-Fill Indicators**: Visually indicate which fields are auto-filled vs user-edited.

7. **Provide Clear Feedback**: Show source and confidence of auto-filled values.

8. **Handle Errors**: Always check `provider.error` and display to user.

## Testing

```dart
testWidgets('FormFillProvider auto-fills form fields', (tester) async {
  final mockFormRepo = MockInspectorFormRepository();
  final mockResponseRepo = MockFormResponseRepository();
  final mockFieldRegistryRepo = MockFormFieldRegistryRepository();
  final autoFillEngine = AutoFillEngine();

  await tester.pumpWidget(
    MaterialApp(
      home: ChangeNotifierProvider(
        create: (_) => FormFillProvider(
          mockFormRepo,
          mockResponseRepo,
          mockFieldRegistryRepo,
          autoFillEngine,
        ),
        child: const FormFillScreen(),
      ),
    ),
  );

  final provider = tester.read<FormFillProvider>();

  // Load form
  await provider.loadForm(formId: 'test-form');
  await tester.pump();

  // Auto-fill
  await provider.autoFillAll(
    context: AutoFillContext(inspectorName: 'Test Inspector'),
  );
  await tester.pump();

  expect(provider.fieldValues['inspector_name'], 'Test Inspector');
  expect(provider.isFieldAutoFilled('inspector_name'), true);
});
```

## See Also

- `lib/features/toolbox/data/services/auto_fill_engine.dart` - Auto-fill logic
- `lib/features/toolbox/data/services/auto_fill_context_builder.dart` - Context building
- `lib/features/toolbox/presentation/providers/form_fill_provider.dart` - Provider implementation
- `lib/features/toolbox/data/models/auto_fill_result.dart` - Result models
