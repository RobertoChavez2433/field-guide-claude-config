# Toolbox Implementation Remediation Plan

**Created**: 2026-01-27
**Status**: Pending Review
**Scope**: Fix gaps and incorrect implementations from Phases 0-11

---

## Executive Summary

After a thorough audit comparing the implementation plan against actual code, I found:
- **3 Critical gaps** (broken functionality)
- **2 Medium gaps** (missing features)
- **8 Missing tests** (required by plan but not implemented)
- **Multiple features correctly implemented**

---

## Critical Issues (Broken Functionality)

### Issue 1: Sync Not Registered (Phase 4.3 SKIPPED)

**Plan Requirement** (Phase 4.3):
> "Create `*RemoteDatasource` classes for each new table."
> "Register in `lib/services/sync_service.dart` `_initDatasources()` method."

**Actual State**:
- NO remote datasources exist at `lib/features/toolbox/data/datasources/remote/`
- `SyncService._initDatasources()` has NO references to toolbox tables
- All toolbox data (forms, responses, todos, calculations) is **LOCAL ONLY**

**Impact**: Users lose all toolbox data if they switch devices. No backup.

**Fix Required**:
1. Create 4 remote datasources:
   - `inspector_form_remote_datasource.dart`
   - `form_response_remote_datasource.dart`
   - `todo_item_remote_datasource.dart`
   - `calculation_history_remote_datasource.dart`
2. Register in `SyncService._initDatasources()`
3. Add sync queue operations

**Files**: 5 new, 1 modified

---

### Issue 2: PDF Field Names Not Mapped to Actual Template Fields (Phase 8.1)

**Plan Requirement** (Phase 8.1):
> "Map form fields to PDF template field names."

**Actual State**:
- `FormSeedService` defines generic pdfField names: `project_number`, `slump`, `air_content`, etc.
- Actual PDF templates have **UNKNOWN field names** (not investigated)
- `FormPdfService._setField()` logs "Field not found" for unmapped fields
- **Exported PDFs are likely BLANK**

**Impact**: PDF export feature is non-functional.

**Fix Required**:
1. Generate debug PDFs using `FormPdfService.generateDebugPdf()` to discover actual field names
2. Update `FormSeedService` with correct `pdfField` mappings
3. Test PDF export

**Files**: 1 modified (+ investigation)

---

### Issue 3: Auto-Fill From Context Very Limited (Phase 6.2)

**Plan Requirement** (Phase 6.2):
> "Auto-fill fields from project/entry data."

**Actual State** (`form_fill_screen.dart:122-148`):
Only 2 fields auto-filled:
- `project_number` (from project)
- `date` (current date)

**Missing**:
| Field | Source |
|-------|--------|
| `contractor` | Prime contractor from project/entry |
| `location` | Entry location or project default |
| `inspector` | Inspector name from Settings |

**Impact**: Users must manually enter data that should auto-populate.

**Fix**: Expand `_autoFillFromContext()` to include more fields.

**Files**: 1 modified

---

## Medium Issues (Missing Features)

### Issue 4: IDR Attachments Not Integrated (Phase 8.2)

**Plan Requirement** (Phase 8.2):
> "Add filenames to IDR attachments (same pattern as photos)."

**Actual State**: No integration between form PDF exports and IDR (Inspector's Daily Report). Grep for "IDR" in toolbox code returns no matches.

**Impact**: Exported form PDFs are standalone files, not linked to daily reports.

**Fix**: Add form PDF filenames to IDR attachments when exporting.

---

### Issue 5: Table Rows Not Filling PDF Correctly (Phase 8)

**Actual State** (`form_pdf_service.dart:79-85`):
```dart
if (tableRows.isNotEmpty) {
  _setField(form, 'notes', summaryText);
  _setField(form, 'results', summaryText);
  _setField(form, 'test_results', summaryText);
}
```

**Problem**: Tries generic field names that probably don't exist in PDF templates. Test results should go to specific table cells in the PDF, not a notes field.

**Fix**: Investigate MDOT form table structure and implement proper row-by-row filling.

---

## Missing Tests (Required by Plan)

The plan specifies tests for each phase. These are **MISSING**:

### Phase 5 Tests (Forms Data Layer)
| Test Type | Requirement | Status |
|-----------|-------------|--------|
| Unit | Model serialization | Exists in database test |
| Unit | Datasource CRUD | **MISSING** |
| Widget | Forms list displays seeded forms | **MISSING** |

### Phase 6 Tests (Forms UI)
| Test Type | Requirement | Status |
|-----------|-------------|--------|
| Widget | Hybrid input populates fields and creates table rows | **MISSING** |
| Unit | UI logic for add-row and clearing input | **MISSING** |

### Phase 9 Tests (Calculator)
| Test Type | Requirement | Status |
|-----------|-------------|--------|
| Unit | Calculator formula validation | EXISTS |
| Widget | Calculator UI flow and result return | **MISSING** |

### Phase 10 Tests (Gallery)
| Test Type | Requirement | Status |
|-----------|-------------|--------|
| Widget | Gallery grid loads photos | **MISSING** |
| Patrol | Navigation to gallery from toolbox | EXISTS (nav_flow) |

### Phase 11 Tests (To-Do's)
| Test Type | Requirement | Status |
|-----------|-------------|--------|
| Unit | CRUD on todo items | **MISSING** |
| Widget | Completion toggles and sorting | **MISSING** |

**Files to Create**:
- `test/features/toolbox/data/datasources/inspector_form_local_datasource_test.dart`
- `test/features/toolbox/data/datasources/todo_item_local_datasource_test.dart`
- `test/features/toolbox/presentation/screens/forms_list_screen_test.dart`
- `test/features/toolbox/presentation/screens/form_fill_screen_test.dart`
- `test/features/toolbox/presentation/screens/calculator_screen_test.dart`
- `test/features/toolbox/presentation/screens/gallery_screen_test.dart`
- `test/features/toolbox/presentation/screens/todos_screen_test.dart`

---

## Minor Issues

### Issue 6: Deprecated Key Still Present

`lib/shared/testing_keys.dart:66-68`:
```dart
@Deprecated('Use dashboardToolboxCard instead')
static const dashboardLocationsCard = Key('dashboard_locations_card');
```

**Status**: Can remain for backward compatibility or be removed after verification.

---

## Verified Working (No Changes Needed)

| Feature | Location | Evidence |
|---------|----------|----------|
| Natural Sort | `lib/shared/utils/natural_sort.dart` | Comprehensive tests exist |
| Natural Sort Tests | `test/shared/natural_sort_test.dart` | All edge cases covered |
| ProjectSettingsProvider | Provider + tests | Full coverage |
| Auto-load Toggle | Settings UI | Wired correctly |
| Main.dart Auto-Load | Lines 286-300 | Loads on startup |
| Database Tables | Version 13, 18 tables | Tests verify |
| Supabase Migration | RLS policies | Exists |
| Form Templates | assets/templates/forms/ | Both PDFs present |
| Calculator Service | HMA + Concrete | Full test coverage |
| Calculator History | Saves via datasource | Works |
| Gallery Filtering | Date + entry filters | Code review verified |
| To-Do CRUD | Provider methods | Code review verified |
| Form Parsing | Keywords, synonyms | Full test coverage |
| Parsing Confirmation UI | `_confirmParsedValues()` | Editable preview |
| Dashboard Card | Locations to Toolbox | Tests updated |
| Patrol Tests | Navigation + coverage | Updated |
| Toolbox Routes | All 5 registered | Verified |
| Provider Registration | All in main.dart | Verified |

---

## Implementation Priority

### Phase A: Critical Fixes (Must Have)

1. **A1: PDF Field Mapping** - Core feature broken
2. **A2: Auto-Fill Enhancement** - UX improvement
3. **A3: Sync Registration** - Data durability

### Phase B: Missing Tests (Should Have)

4. **B1: Widget Tests** - Plan compliance
5. **B2: Unit Tests** - Plan compliance

### Phase C: Features (Nice to Have)

6. **C1: IDR Attachments** - Integration
7. **C2: Table Row PDF Filling** - Better output

---

## Validation Checklist

After fixes, verify:

- [ ] PDF export fills all fields correctly (test both MDOT forms)
- [ ] Auto-fill populates inspector name, contractor, location
- [ ] Sync uploads toolbox data to Supabase
- [ ] Table rows appear in exported PDF
- [ ] All new tests pass
- [ ] All existing tests pass (`flutter test`)
- [ ] Analyzer: 0 errors
