# Template Validation API Reference

## Quick Reference for Template Storage & Validation

---

## Core Types

### RemapStatus (Enum)
```dart
enum RemapStatus {
  upToDate,        // Mappings are current
  templateChanged, // Template modified, needs re-mapping
  noMapping,       // No field mappings exist
}
```

### TemplateValidationStatus (Enum)
```dart
enum TemplateValidationStatus {
  valid,                 // Template exists and unchanged
  missingButRecoverable, // File missing, bytes stored
  hashMismatch,          // File modified since mapping
  invalid,               // No recovery possible
}
```

### TemplateValidationResult (Class)
```dart
class TemplateValidationResult {
  final TemplateValidationStatus status;
  final String message;
  final Uint8List? recoveredBytes;

  bool get isValid;         // status == valid
  bool get isRecoverable;   // status == missingButRecoverable
  bool get hasIssues;       // hashMismatch or invalid
}
```

---

## FieldRegistryService Methods

### Hash Computation

#### `computeTemplateHash(Uint8List bytes) → String`
Generates SHA-256 hash of template bytes.

**Parameters**:
- `bytes`: PDF template content as Uint8List

**Returns**: 64-character hex string (SHA-256 hash)

**Example**:
```dart
final pdfBytes = await File('template.pdf').readAsBytes();
final hash = service.computeTemplateHash(Uint8List.fromList(pdfBytes));
// hash: "a3c5f1b2..." (64 chars)
```

---

### Change Detection

#### `checkTemplateChanged(InspectorForm form, Uint8List currentBytes) → Future<bool>`
Checks if template has been modified since last mapping.

**Parameters**:
- `form`: Inspector form with stored hash
- `currentBytes`: Current template bytes to check

**Returns**: `true` if hash differs, `false` if matches or no stored hash

**Example**:
```dart
final currentBytes = await File(form.templatePath).readAsBytes();
final changed = await service.checkTemplateChanged(
  form,
  Uint8List.fromList(currentBytes),
);

if (changed) {
  print('Template modified! Re-mapping recommended.');
}
```

---

### Re-mapping Status

#### `getRemapStatus(InspectorForm form, Uint8List? currentBytes) → Future<RemapStatus>`
Determines if form needs field re-mapping.

**Parameters**:
- `form`: Inspector form to check
- `currentBytes`: Optional current template bytes (null skips hash check)

**Returns**: RemapStatus enum value

**Example**:
```dart
final status = await service.getRemapStatus(form, currentBytes);

switch (status) {
  case RemapStatus.noMapping:
    print('No mappings yet - create initial mapping');
    break;
  case RemapStatus.templateChanged:
    print('Template changed - re-mapping required');
    break;
  case RemapStatus.upToDate:
    print('Mappings are current');
    break;
}
```

---

### Template Validation

#### `validateTemplate(InspectorForm form) → Future<TemplateValidationResult>`
Comprehensive template validation with recovery options.

**Parameters**:
- `form`: Inspector form to validate

**Returns**: TemplateValidationResult with status and recovery data

**Validation Logic**:
1. **Asset templates**: Always valid (shipped with app)
2. **File templates**:
   - File exists + hash matches → `valid`
   - File exists + hash differs → `hashMismatch`
   - File missing + bytes stored → `missingButRecoverable`
   - File missing + no bytes → `invalid`
3. **Remote/Unknown**: `invalid`

**Example**:
```dart
final result = await service.validateTemplate(form);

if (result.isValid) {
  print('✓ Template ready to use');
} else if (result.isRecoverable) {
  print('⚠ File missing but can restore');
  if (await service.restoreTemplateFile(form)) {
    print('✓ Restored successfully');
  }
} else if (result.status == TemplateValidationStatus.hashMismatch) {
  print('⚠ Template modified - mappings may be incorrect');
} else {
  print('✗ Template unavailable');
}
```

---

### Template Restoration

#### `restoreTemplateFile(InspectorForm form) → Future<bool>`
Restores template file from stored bytes.

**Parameters**:
- `form`: Inspector form with templateBytes stored

**Returns**: `true` if restored successfully, `false` otherwise

**Behavior**:
- Creates parent directories if needed
- Overwrites existing file if present
- Returns `false` if no bytes stored or write fails

**Example**:
```dart
if (form.templateBytes != null) {
  final restored = await service.restoreTemplateFile(form);
  if (restored) {
    print('Template restored to: ${form.templatePath}');
  } else {
    print('Failed to restore template');
  }
} else {
  print('No stored bytes available for recovery');
}
```

---

## Complete Workflow Example

### Import Template with Storage
```dart
// 1. User selects PDF file
final pickedFile = await FilePicker.platform.pickFiles(
  type: FileType.custom,
  allowedExtensions: ['pdf'],
);

if (pickedFile != null) {
  final file = File(pickedFile.files.single.path!);
  final bytes = await file.readAsBytes();
  final bytesUint8 = Uint8List.fromList(bytes);

  // 2. Compute hash
  final hash = fieldRegistryService.computeTemplateHash(bytesUint8);

  // 3. Create form with stored bytes + hash
  final form = InspectorForm(
    projectId: currentProject.id,
    name: 'Imported Form',
    templatePath: file.path,
    templateSource: TemplateSource.file,
    templateHash: hash,
    templateBytes: bytesUint8, // Store for recovery
  );

  // 4. Save to database
  await formRepository.create(form);

  // 5. Proceed to field mapping...
}
```

### Validate Before Use
```dart
// Before opening form for editing
final validation = await fieldRegistryService.validateTemplate(form);

if (validation.hasIssues) {
  if (validation.isRecoverable) {
    // Offer restoration
    final shouldRestore = await showConfirmDialog(
      'Template file missing. Restore from stored copy?',
    );

    if (shouldRestore) {
      await fieldRegistryService.restoreTemplateFile(form);
      // Re-validate
      final recheck = await fieldRegistryService.validateTemplate(form);
      if (!recheck.isValid) {
        showError('Failed to restore template');
        return;
      }
    }
  } else if (validation.status == TemplateValidationStatus.hashMismatch) {
    // Warn about changes
    showWarning(
      'Template has been modified since last mapping. '
      'Field positions may be incorrect.',
    );
  } else {
    showError('Template unavailable: ${validation.message}');
    return;
  }
}

// Proceed with form
openFormEditor(form);
```

### Check Re-mapping Need
```dart
// Periodic check or on form edit
final currentFile = File(form.templatePath);
if (await currentFile.exists()) {
  final currentBytes = await currentFile.readAsBytes();
  final status = await fieldRegistryService.getRemapStatus(
    form,
    Uint8List.fromList(currentBytes),
  );

  if (status == RemapStatus.templateChanged) {
    final shouldRemap = await showConfirmDialog(
      'Template has changed. Re-map field positions?',
    );

    if (shouldRemap) {
      navigateToFieldMapping(form);
    }
  }
}
```

---

## Database Schema

### inspector_forms table
```sql
CREATE TABLE inspector_forms (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  name TEXT NOT NULL,
  template_path TEXT NOT NULL,
  template_hash TEXT,           -- SHA-256 hash for drift detection
  template_bytes BLOB,          -- Full PDF for recovery
  template_version INTEGER DEFAULT 1,
  template_field_count INTEGER,
  template_source TEXT DEFAULT 'asset',
  -- ... other fields
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

---

## Testing

Run template validation tests:
```bash
flutter test test/features/toolbox/services/template_validation_test.dart
```

All 24 tests should pass:
- ✓ Hash computation (5 tests)
- ✓ Change detection (3 tests)
- ✓ Remap status (4 tests)
- ✓ Validation scenarios (6 tests)
- ✓ File restoration (5 tests)
- ✓ End-to-end workflow (1 test)

---

## Error Handling

### Common Scenarios

**File Missing**:
```dart
final result = await service.validateTemplate(form);
if (result.status == TemplateValidationStatus.missingButRecoverable) {
  await service.restoreTemplateFile(form);
}
```

**Hash Mismatch**:
```dart
if (result.status == TemplateValidationStatus.hashMismatch) {
  // Prompt user to update or restore
  final action = await showChoiceDialog([
    'Continue with modified template',
    'Restore original template',
    'Re-map fields for new template',
  ]);
}
```

**No Recovery Possible**:
```dart
if (result.status == TemplateValidationStatus.invalid) {
  // Template lost, must re-import
  showError('Template unavailable. Please re-import.');
}
```

---

## Performance Notes

- **Hash Computation**: O(n) where n = file size (~1ms for 1MB PDF)
- **Validation**: Single file stat + optional hash check (~2ms)
- **Restoration**: File write operation (~10ms for 1MB PDF)
- **Database Storage**: BLOB stored inline, efficient for <5MB PDFs

For large templates (>10MB), consider storing reference instead of bytes.
