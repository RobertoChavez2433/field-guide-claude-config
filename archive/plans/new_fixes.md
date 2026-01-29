# Toolbox Phase 5/8 Completion Plan

## Summary
Fix 6 gaps in Phase 5 (Auto-Fill) and Phase 8 (PDF Field Discovery + Mapping) implementations.

## Issues & Priority

| # | Issue | Priority | Risk | Impact |
|---|-------|----------|------|--------|
| 1 | Imported templates cannot render | **P0** | Low | Blocking - imports unusable |
| 2 | FormPreviewTab bypasses DI/cache | P1 | Low | Performance degradation |
| 3 | Template hash never set | P1 | Low | Blocks validation |
| 4 | Validation/remapping not called | P2 | Medium | No drift detection |
| 5 | Auto-fill provenance not persisted | P2 | Medium | "Clear auto-filled" lost on reopen |
| 6 | Context hydration not guaranteed | P2 | Low | Auto-fill may get nulls |

---

## Step 1: Fix Template Rendering (P0 - BLOCKING)

**File:** `lib/features/toolbox/data/services/form_pdf_service.dart`

**Change** `generateFormPdf()` (lines 182-203) to check `templateSource`:

```dart
// Add before document creation (around line 186)
final Uint8List pdfBytes;

if (data.form.templateSource == TemplateSource.file ||
    data.form.templateSource == TemplateSource.remote) {
  // Imported templates: use stored bytes
  if (data.form.templateBytes == null) {
    throw TemplateLoadException(
      templatePath: data.form.templatePath,
      message: 'Imported template has no stored bytes. Re-import required.',
    );
  }
  pdfBytes = data.form.templateBytes!;
  debugPrint('[FormPDF] Using stored bytes for imported template');
} else {
  // Asset templates: use rootBundle
  try {
    final templateData = await rootBundle.load(data.form.templatePath);
    pdfBytes = templateData.buffer.asUint8List();
  } on FlutterError catch (e) {
    // existing error handling...
  }
}

// Use pdfBytes instead of templateBytes.buffer.asUint8List()
document = PdfDocument(inputBytes: pdfBytes);
```

**Also update:** `generateDebugPdf()` (lines 725-757) with same logic.

**Verify:** Import PDF -> Map fields -> Save -> Open form -> Preview tab renders.

---

## Step 2: Fix FormPreviewTab DI (P1)

**File:** `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`

**Change** line 57 to use Provider instead of direct instantiation:

```dart
// Before:
final pdfService = FormPdfService();

// After:
final pdfService = context.read<FormPdfService>();
```

**Ensure** `_generatePreview()` is called via `addPostFrameCallback` for context access:

```dart
@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _generatePreview();
  });
}
```

**Verify:** Debug logs show `[FormPDF Cache] HIT` on repeated preview opens.

---

## Step 3: Set Template Hash on Save (P1)

**File:** `lib/features/toolbox/presentation/providers/field_mapping_provider.dart`

**Add** import and helper:
```dart
import 'package:crypto/crypto.dart';

String _computeTemplateHash(Uint8List bytes) {
  final digest = sha256.convert(bytes);
  return digest.toString();
}
```

**Modify** `saveForm()` (around line 295):
```dart
final templateHash = _pdfBytes != null
    ? _computeTemplateHash(_pdfBytes!)
    : null;

final form = InspectorForm(
  // ... existing fields ...
  templateHash: templateHash,  // ADD THIS
);
```

**Verify:** `SELECT template_hash FROM inspector_forms WHERE is_builtin = 0` returns 64-char hex.

---

## Step 4: Wire Template Validation (P2)

**File:** `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

**Add** state variables:
```dart
TemplateValidationResult? _templateValidation;
bool _templateWarningDismissed = false;
```

**Add** validation in `_loadData()` after form loads:
```dart
if (form.templateSource != TemplateSource.asset) {
  final fieldRegistryService = context.read<FieldRegistryService>();
  final validation = await fieldRegistryService.validateTemplate(form);

  if (validation.hasIssues) {
    _templateValidation = validation;
  } else if (validation.isRecoverable) {
    await fieldRegistryService.restoreTemplateFile(form);
  }
}
```

**Add** warning banner widget in build method.

**Verify:** Delete imported template file -> Reopen form -> See warning/recovery.

---

## Step 5: Persist Auto-fill Provenance (P2)

### 5a. Database Migration

**File:** `lib/core/database/database_service.dart`

Bump version to 18, add migration:
```dart
if (oldVersion < 18) {
  await db.execute('''
    ALTER TABLE form_responses ADD COLUMN provenance_metadata TEXT
  ''');
}
```

### 5b. Extend FormResponse Model

**File:** `lib/features/toolbox/data/models/form_response.dart`

Add field + helper:
```dart
final String? provenanceMetadata;

Map<String, AutoFillResult> get parsedProvenanceMetadata {
  if (provenanceMetadata == null) return {};
  final decoded = jsonDecode(provenanceMetadata!) as Map<String, dynamic>;
  return decoded.map((k, v) => MapEntry(k, AutoFillResult.fromMap(v)));
}
```

Update constructor, copyWith, toMap, fromMap.

### 5c. Save/Restore in FormFillScreen

**File:** `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

Restore on load:
```dart
final savedProvenance = response.parsedProvenanceMetadata;
for (final entry in savedProvenance.entries) {
  if (!_userEditedFields.contains(entry.key)) {
    _autoFillResults[entry.key] = entry.value;
  }
}
```

Save on save:
```dart
final provenanceJson = jsonEncode(_autoFillResults.map((k, v) => MapEntry(k, v.toMap())));
final updated = _response!.copyWith(
  responseData: jsonEncode(values),
  provenanceMetadata: provenanceJson,
);
```

**Verify:** Fill form -> Save -> Reopen -> Auto-fill indicators preserved.

---

## Step 6: Ensure Context Hydration (P2)

**File:** `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

**Add** in `_loadData()` before auto-fill:
```dart
if (projectId != null) {
  final contractorProvider = context.read<ContractorProvider>();
  if (contractorProvider.contractors.isEmpty) {
    await contractorProvider.loadContractors(projectId);
  }

  final locationProvider = context.read<LocationProvider>();
  if (locationProvider.locations.isEmpty) {
    await locationProvider.loadLocations(projectId);
  }
}

if (response.entryId != null) {
  final entryProvider = context.read<DailyEntryProvider>();
  if (!entryProvider.entries.any((e) => e.id == response.entryId)) {
    await entryProvider.loadEntries(projectId!);
  }
}
```

**Verify:** Clear app data -> Deep link to form -> Auto-fill works.

---

## Implementation Order

```
Step 1 (Template Rendering) - BLOCKING
    ↓
Step 2 (DI/Cache) + Step 3 (Hash) - parallel
    ↓
Step 4 (Validation) - depends on Step 3
    ↓
Step 5 (Provenance) - can parallel with Step 4
    ↓
Step 6 (Context Hydration)
```

---

## Critical Files

| File | Changes |
|------|---------|
| `lib/features/toolbox/data/services/form_pdf_service.dart` | Step 1: Template source check |
| `lib/features/toolbox/presentation/widgets/form_preview_tab.dart` | Step 2: Use Provider DI |
| `lib/features/toolbox/presentation/providers/field_mapping_provider.dart` | Step 3: Compute hash |
| `lib/features/toolbox/presentation/screens/form_fill_screen.dart` | Steps 4, 5c, 6: Validation, provenance, hydration |
| `lib/core/database/database_service.dart` | Step 5a: Migration v18 |
| `lib/features/toolbox/data/models/form_response.dart` | Step 5b: Add provenance field |

---

## Verification

1. **Unit Tests**: Run existing toolbox tests
2. **Import Flow**: Import PDF -> Map -> Fill -> Preview -> Export
3. **Provenance**: Auto-fill -> Save -> Reopen -> Verify indicators
4. **Validation**: Modify/delete template file -> Reopen form -> See warning
5. **Flutter Analyze**: 0 new errors

---

# Additional Issues (Phase 13 + Infrastructure Gaps)

## Issues Summary

| # | Issue | Priority | Risk | Impact |
|---|-------|----------|------|--------|
| 7 | Supabase missing template columns | P1 | Medium | Template data not synced |
| 8 | PagedListProvider not used | P2 | Low | Code duplication |
| 9 | Pagination UI widgets unused | P2 | Low | No infinite scroll in screens |
| 10 | Shared dialogs not used | P3 | Low | Code duplication in settings |

---

## Step 7: Supabase Template Columns (P1)

**Problem:** Supabase `inspector_forms` table missing 5 columns that exist in local SQLite. Sync silently ignores these fields.

**Missing columns:**
- `template_source` (TEXT)
- `template_hash` (TEXT)
- `template_version` (INTEGER)
- `template_field_count` (INTEGER)
- `template_bytes` (BYTEA)

**File:** `supabase/migrations/20260129000000_template_columns.sql` (new)

```sql
-- Add missing template columns to inspector_forms
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS template_source TEXT DEFAULT 'asset';
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS template_hash TEXT;
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS template_version INTEGER DEFAULT 1;
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS template_field_count INTEGER;
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS template_bytes BYTEA;

-- Add index for template_hash lookups
CREATE INDEX IF NOT EXISTS idx_inspector_forms_template_hash ON inspector_forms(template_hash);
```

**Verify:** After running migration, sync inspector_forms and check all columns populated.

---

## Step 8: Consolidate Pagination in Providers (P2)

**Problem:** `PagedListProvider` exists but 3 providers implement manual pagination instead of extending it.

**Current state:**
- `PagedListProvider` in `lib/shared/providers/paged_list_provider.dart` - complete, unused
- `DailyEntryProvider`, `BidItemProvider`, `PhotoProvider` - duplicate pagination logic

**Option A (Preferred):** Keep current manual implementations, document as intentional
- Providers already work, pagination methods are backwards-compatible
- Refactoring to PagedListProvider would be breaking change

**Option B:** Refactor to extend PagedListProvider
- Reduces ~150 lines of duplicate code
- Requires updating all callers

**Recommendation:** Document as-is, defer refactoring to Phase 14 (DRY/KISS).

---

## Step 9: Wire Pagination UI to Screens (P2)

**Problem:** Pagination widgets exist but no screen uses them.

**Widgets available:**
- `PaginatedListView<T>` - Infinite scroll with auto-load
- `PaginatedSliverList<T>` - Sliver version
- `PaginationInfo`, `PaginationButtons`, `PaginationBar`

**Screens that should use pagination:**
| Screen | Current | Should Use |
|--------|---------|------------|
| `entries_list_screen.dart` | `loadEntries()` → loads ALL | `PaginatedListView` + `loadMoreEntries()` |
| `project_list_screen.dart` | `loadProjects()` → loads ALL | `PaginatedListView` + paged loading |
| `quantities_screen.dart` | `loadBidItems()` → loads ALL | `PaginatedListView` + `loadMoreItems()` |

**Example change for entries_list_screen.dart:**
```dart
// Replace ListView.builder with:
PaginatedListView<DailyEntry>(
  items: provider.pagedItems,
  hasMore: provider.hasMoreEntries,
  isLoading: provider.pagedLoading,
  onLoadMore: () => provider.loadMoreEntries(),
  itemBuilder: (context, entry) => EntryListTile(entry: entry),
)
```

**Recommendation:** Defer to Phase 14 - requires screen updates and testing.

---

## Step 10: Migrate Settings Dialogs to Shared (P3)

**Problem:** Settings screen has 7 inline dialogs instead of using shared patterns.

**Current inline dialogs in settings_screen.dart:**
1. `_showEditInspectorNameDialog()` (line 543)
2. `_showEditInitialsDialog()` (line 601)
3. `_showEditInspectorPhoneDialog()` (line 680)
4. `_showEditInspectorCertDialog()` (line 735)
5. `_showEditInspectorAgencyDialog()` (line 790)
6. `_showClearDataDialog()` (line 845)
7. `_showSignOutDialog()` (line 921)

**Should use:**
- `confirmation_dialog.dart` for sign-out and clear data
- Shared text input dialog for inspector fields

**Also affected:**
- `personnel_types_screen.dart` - 3 inline dialogs

**Recommendation:** Low priority. Defer to Phase 15 (Large File Decomposition).

---

## Updated Implementation Order

```
Phase A: Toolbox Critical (Steps 1-6)
    Step 1 (Template Rendering) - BLOCKING
        ↓
    Step 2 + Step 3 - parallel
        ↓
    Step 4 (Validation) - depends on Step 3
        ↓
    Step 5 (Provenance) - parallel with Step 4
        ↓
    Step 6 (Context Hydration)

Phase B: Sync Fix (Step 7)
    Step 7 (Supabase Migration) - independent, can run anytime

Phase C: Deferred (Steps 8-10)
    Document for Phase 14/15
```

---

## Additional Files

| File | Changes |
|------|---------|
| `supabase/migrations/20260129000000_template_columns.sql` | Step 7: New migration |
| `.claude/plans/COMPREHENSIVE_PLAN.md` | Steps 8-10: Document for future phases |

---

## Deferred Items (Document Only)

These items are documented for future phases:

1. **Phase 14 (DRY/KISS):**
   - Consolidate provider pagination to PagedListProvider
   - Wire pagination UI to entries/projects/quantities screens

2. **Phase 15 (Large File Decomposition):**
   - Extract settings screen dialogs to shared widgets
   - Extract personnel type dialogs
