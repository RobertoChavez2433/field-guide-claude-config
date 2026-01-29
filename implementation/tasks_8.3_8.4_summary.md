# Tasks 8.3 + 8.4: Template Storage and Validation - Implementation Summary

## Completed: 2026-01-28

### Overview
Implemented template storage with hash-based change detection and validation for imported PDF templates in the Inspector Forms system.

---

## Task 8.3: Template Storage + Re-mapping Detection

### 1. Database Schema Update
**File**: `lib/core/database/database_service.dart`

- Added `template_bytes BLOB` column to `inspector_forms` table
- Updated database version from 16 to 17
- Added migration in `_onUpgrade` for existing databases

**Migration**:
```sql
ALTER TABLE inspector_forms ADD COLUMN template_bytes BLOB;
```

### 2. InspectorForm Model Update
**File**: `lib/features/toolbox/data/models/inspector_form.dart`

Added field and serialization support:
- `final Uint8List? templateBytes` - Stores full PDF template for persistence
- Updated constructor, `copyWith`, `toMap`, `fromMap`
- SQLite automatically handles BLOB as Uint8List

### 3. Template Hash Service
**File**: `lib/features/toolbox/data/services/field_registry_service.dart`

Implemented hash-based change detection:

**New Enum** (top-level):
```dart
enum RemapStatus {
  upToDate,        // No changes
  templateChanged, // Hash differs, re-mapping recommended
  noMapping,       // No mappings exist yet
}
```

**New Methods**:
- `computeTemplateHash(Uint8List bytes)` - SHA-256 hash generation
- `checkTemplateChanged(InspectorForm, Uint8List)` - Detects template modifications
- `getRemapStatus(InspectorForm, Uint8List?)` - Returns re-mapping recommendation

### 4. Dependencies
**File**: `pubspec.yaml`

Added: `crypto: ^3.0.6` for SHA-256 hashing

---

## Task 8.4: Imported Template Persistence Validation

### 1. Validation Result Model
**File**: `lib/features/toolbox/data/models/template_validation_result.dart` (NEW)

```dart
enum TemplateValidationStatus {
  valid,                 // Template exists and matches
  missingButRecoverable, // File missing but bytes stored
  hashMismatch,          // File exists but content changed
  invalid,               // Template unavailable
}

class TemplateValidationResult {
  final TemplateValidationStatus status;
  final String message;
  final Uint8List? recoveredBytes;

  bool get isValid;
  bool get isRecoverable;
  bool get hasIssues;
}
```

### 2. Validation & Restoration Methods
**File**: `lib/features/toolbox/data/services/field_registry_service.dart`

**New Methods**:
- `validateTemplate(InspectorForm)` - Comprehensive validation
  - Asset templates: Always valid
  - File templates: Check existence, hash match
  - Returns recovery options if file missing

- `restoreTemplateFile(InspectorForm)` - Restores from stored bytes
  - Creates parent directories if needed
  - Returns success/failure status

### 3. Barrel Export
**File**: `lib/features/toolbox/data/models/models.dart`

Added: `export 'template_validation_result.dart';`

---

## Comprehensive Test Suite

### File: `test/features/toolbox/services/template_validation_test.dart`

**24 tests covering**:

1. **Template Hash Computation** (5 tests)
   - Consistency verification
   - Collision detection
   - SHA-256 format validation
   - Edge cases (empty, large files)

2. **Template Change Detection** (3 tests)
   - Hash matching
   - Mismatch detection
   - Null hash handling

3. **Remap Status** (4 tests)
   - No mappings scenario
   - Up-to-date detection
   - Template change detection
   - Null bytes handling

4. **Template Validation** (6 tests)
   - Asset template validation
   - File existence + hash match
   - Hash mismatch detection
   - Missing but recoverable
   - Invalid (no recovery)
   - Unknown source handling

5. **Template Restoration** (5 tests)
   - Successful restoration
   - Parent directory creation
   - No bytes handling
   - File system error handling
   - Overwrite existing file

6. **End-to-End Flow** (1 test)
   - Import → Validate → Modify → Detect → Restore

**All 24 tests passing ✓**

---

## Key Features

### Hash-Based Change Detection
- SHA-256 hashing ensures reliable drift detection
- Detects even minor template modifications
- Prevents mapping errors from template updates

### Persistence & Recovery
- Full template stored as BLOB in database
- Automatic recovery if source file missing
- Maintains portability across environments

### Validation States
1. **Valid**: Template accessible, unchanged
2. **Missing but Recoverable**: File gone, bytes available
3. **Hash Mismatch**: Template modified, re-mapping needed
4. **Invalid**: Template unavailable, cannot proceed

### Re-mapping Workflow
```
1. Import template → Store bytes + hash
2. Create field mappings
3. Periodic validation checks hash
4. If changed → RemapStatus.templateChanged
5. User prompted to re-map fields
6. New hash stored after re-mapping
```

---

## Integration Points

### Future Usage in UI
```dart
// Validate template before using
final validation = await fieldRegistryService.validateTemplate(form);

if (validation.isRecoverable) {
  // Offer restoration
  final restored = await fieldRegistryService.restoreTemplateFile(form);
  if (restored) {
    showSnackbar('Template restored successfully');
  }
} else if (validation.status == TemplateValidationStatus.hashMismatch) {
  // Warn user
  showDialog('Template has changed. Field mappings may be incorrect.');
}

// Check if re-mapping needed
final remapStatus = await fieldRegistryService.getRemapStatus(form, currentBytes);
if (remapStatus == RemapStatus.templateChanged) {
  showDialog('Template updated. Please re-map fields.');
}
```

---

## Files Modified

1. `lib/core/database/database_service.dart` - Schema + migration
2. `lib/features/toolbox/data/models/inspector_form.dart` - Model update
3. `lib/features/toolbox/data/services/field_registry_service.dart` - Hash + validation logic
4. `pubspec.yaml` - Added crypto package
5. `lib/features/toolbox/data/models/template_validation_result.dart` - NEW model
6. `lib/features/toolbox/data/models/models.dart` - Barrel export
7. `test/features/toolbox/services/template_validation_test.dart` - NEW comprehensive tests

---

## Quality Metrics

- **Test Coverage**: 24 comprehensive tests, all passing
- **Analyzer**: 0 errors in modified files
- **Database Version**: Bumped to v17 with migration
- **Documentation**: Full inline documentation on all public methods

---

## Next Steps (Future Tasks)

1. **UI Integration**: Add validation checks to form import/edit screens
2. **Auto-Restore**: Automatic recovery attempt when missing file detected
3. **Version History**: Track template version changes over time
4. **Batch Validation**: Check all forms in project for template drift
5. **User Notifications**: Alert when templates need re-mapping
