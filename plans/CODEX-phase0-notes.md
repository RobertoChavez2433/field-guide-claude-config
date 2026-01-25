# CODEX Phase 0 - Discovery & Testing Impact Report

**Date**: 2026-01-25
**Status**: Complete

## Subphase 0.1 - Inventory Keys + Tests

### Entry Wizard Screen Keys

#### Current Keys in Use
- `entryWizardAddPersonnel` - Static key for "Add personnel type" button (line 853 in entry_wizard_screen.dart)
- Location: Single button in personnel section header
- **Issue**: Single key for all contractors - will cause duplicate key issues when we make it contractor-scoped

#### Test References
**File**: `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
- Line 226: `final addPersonnelButton = $(TestingKeys.entryWizardAddPersonnel);`
- Used to add personnel types during entry creation flow

**File**: `integration_test/patrol/REQUIRED_UI_KEYS.md`
- Line 116: Documents `entryWizardAddPersonnel` as required key

### Report Screen Keys

#### Current Keys in Use
- `reportAddContractorButton` - Button to add contractor to report (line 706 in testing_keys.dart)
- `reportContractorCard(String contractorId)` - Dynamic key for contractor cards (line 715)
- `reportPersonnelCounter(String contractorId, String typeId)` - Dynamic key for personnel counters (line 719)

#### Test References
**File**: `integration_test/patrol/e2e_tests/entry_management_test.dart`
- Line 324: Uses `TestingKeys.reportAddContractorButton`
- Test adds contractors to report and verifies display

### Duplicate Key Analysis

**Current Issue**:
- `entryWizardAddPersonnel` is a single static key
- Entry wizard shows multiple contractors in expansion tiles
- Each contractor section could have an "add personnel type" button
- **Result**: Will have duplicate keys in widget tree when we implement contractor-scoped personnel types

**Planned Solution**:
- Create dynamic key: `entryWizardAddPersonnelButton(String contractorId)`
- Update TestingKeys class with new method
- Update entry wizard UI to use contractor-scoped key
- Update tests to use contractor-scoped key

### Database Schema Analysis

#### Current State (personnel_types table)
```sql
CREATE TABLE personnel_types (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  short_code TEXT,
  sort_order INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
)
```

**Missing Column**: `contractor_id` - Currently personnel types are project-scoped only

#### Current State (entry_personnel_counts table)
```sql
CREATE TABLE entry_personnel_counts (
  id TEXT PRIMARY KEY,
  entry_id TEXT NOT NULL,
  contractor_id TEXT NOT NULL,
  type_id TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
  FOREIGN KEY (contractor_id) REFERENCES contractors(id) ON DELETE CASCADE,
  FOREIGN KEY (type_id) REFERENCES personnel_types(id) ON DELETE CASCADE
)
```

**Current Behavior**: Links counts to contractors at entry level, but types are shared project-wide

### PersonnelType Model Analysis

**File**: `lib/features/contractors/data/models/personnel_type.dart`

**Current Fields**:
- `id`, `projectId`, `name`, `shortCode`, `sortOrder`, `createdAt`, `updatedAt`

**Missing**: `contractorId` field (nullable for backward compatibility)

### Key Files Requiring Changes

#### Schema & Migration
- `lib/core/database/database_service.dart` - Add contractor_id column, migration logic

#### Data Layer
- `lib/features/contractors/data/models/personnel_type.dart` - Add contractorId field
- `lib/features/contractors/data/datasources/local/personnel_type_local_datasource.dart` - Update queries
- `lib/features/contractors/data/datasources/remote/personnel_type_remote_datasource.dart` - Update mapping
- `lib/features/contractors/data/repositories/personnel_type_repository.dart` - Add getByContractor method

#### Presentation Layer
- `lib/features/contractors/presentation/providers/personnel_type_provider.dart` - Cache by contractor
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart` - Contractor-scoped UI
- `lib/features/entries/presentation/screens/report_screen.dart` - Contractor-scoped display

#### Testing Infrastructure
- `lib/shared/testing_keys.dart` - Add entryWizardAddPersonnelButton(contractorId) method
- `integration_test/patrol/REQUIRED_UI_KEYS.md` - Document new key
- `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart` - Update to use scoped key
- `integration_test/patrol/helpers/patrol_test_helpers.dart` - Update helpers if needed

## Subphase 0.2 - Baseline Verification

### Flutter Analyze Results
```
Analyzing field guide app...
No issues found!
```

**Status**: Clean - 0 errors, 0 warnings

### Test Documentation Status

**E2E Tests Related to Personnel**:
1. `entry_lifecycle_test.dart` - Uses `entryWizardAddPersonnel` key (line 226)
2. `entry_management_test.dart` - Uses `reportAddContractorButton` key (line 324)

**Note**: Not running E2E tests per instructions - just documenting what exists for impact analysis

### Migration Strategy

#### Data Preservation Plan
1. Existing project-level personnel types (contractor_id = NULL) will be kept
2. For each contractor in each project, duplicate types with contractor_id set
3. Update entry_personnel_counts to point to new contractor-scoped type_ids
4. Legacy rows remain until validation completes

#### Rollback Safety
- Migration is additive (adding column, not removing data)
- Can revert to project-level types if needed
- entry_personnel_counts will maintain referential integrity via type_id

## Risk Assessment

### High Priority
- **Duplicate Keys**: Entry wizard will have duplicate keys without scoping fix
- **Data Migration**: Must preserve existing entry_personnel_counts mappings correctly
- **Test Coverage**: Must update tests in same PR to avoid breaks

### Medium Priority
- **Supabase Sync**: Remote datasource must handle contractor_id field
- **Provider Caching**: Need efficient cache strategy for contractor-scoped types

### Low Priority
- **UI/UX**: Personnel type dialogs need contractor context passed

## Phase 1 Readiness

**Blockers**: None identified

**Recommended Order**:
1. Database schema update (add column, index)
2. Data migration logic (preserve existing data)
3. Model update (add contractorId field)
4. Datasource updates (local + remote)
5. Repository updates (new methods)
6. Provider updates (contractor-scoped caching)
7. Testing keys update (scoped key method)
8. UI updates (entry wizard + report screen)
9. Test updates (use new scoped keys)
10. Documentation updates (REQUIRED_UI_KEYS.md)

## Key Findings Summary

| Category | Finding | Impact |
|----------|---------|--------|
| Keys | Single static key will cause duplicates | HIGH - Must fix before adding UI |
| Schema | Missing contractor_id column | HIGH - Blocks contractor-scoping |
| Tests | 2 tests reference personnel keys | MEDIUM - Must update in same PR |
| Baseline | Clean analyzer output | LOW - Good starting point |
| Migration | Existing data must be preserved | HIGH - Data integrity critical |

## Next Steps

Proceed to Phase 1 with confidence - all blockers are understood and have clear solutions.
