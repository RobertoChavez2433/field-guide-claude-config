# Pay Application Feature Spec

**Date**: 2026-04-05
**Status**: Approved
**Approach**: Exported-artifact architecture with a unified export history layer, pay-application-specific detail records, and contractor comparison as a pay-app subflow

## Approach Decision

**Selected approach**: Pay Application is a form-like exported artifact, not a live editable form response. It participates in the Forms exported-history experience, persists only when exported, and uses a unified export-history layer shared with IDR, form PDF, and photo exports.

**Key decisions locked in:**
- Pay applications persist only on export.
- Saved pay applications are read-only snapshots in-app.
- If tracked quantities need correction, the inspector edits the tracked data and re-exports.
- Re-exporting the exact same pay-app range prompts the user to replace the saved artifact and reuse the same pay-app number.
- Overlapping non-identical pay-app ranges are blocked.
- Pay-app numbers are chronological, unique per project, auto-assigned with user override.
- Exported Forms history is a filtered exported-artifact browser, separate from editable saved form responses.
- Contractor comparison is part of the pay-app feature and is launched from a saved pay-app detail view.
- Contractor comparison never writes back to tracked data in v1. It produces a standalone discrepancy PDF only.

**Rejected alternatives:**
- **Editable saved pay applications in-app**: rejected. Inspectors should fix source quantities and re-export rather than maintain divergent post-export snapshots inside the app.
- **Change order management in this spec**: removed from scope.
- **Separate pay-app history outside Forms**: rejected. Pay applications should live in the same exported-artifact history surface as other exported document types.

---

## 1. Overview

### Purpose
Build a pay-application export and reconciliation workflow for construction inspectors that:
- generates G703-style pay applications from tracked project quantities
- stores those exports as first-class exported artifacts
- lets inspectors compare a saved pay application against a contractor-supplied pay app
- produces a discrepancy report without mutating project quantities

Simultaneously, this work establishes a unified export-history architecture that replaces the current fragmented export-history model.

### Scope

**Included (5 architectures, 1 spec):**
1. Unified Export History Layer
2. Pay Application Excel Export
3. Exported Forms History Integration
4. Contractor Pay Application Comparison
5. Project Analytics Enhancement

**Excluded:**
- Change order / contract modification management
- Retainage calculations
- Stored materials tracking
- AASHTOWare API integration
- In-app editing of saved exported pay applications
- Automatic write-back from contractor comparison into tracked quantities
- Multi-project aggregation

### Success Criteria
- [ ] All exported artifacts route through a unified export-history layer
- [ ] Pay applications are exported as G703-style `.xlsx` files with correct chaining from prior pay apps
- [ ] Pay-app ranges are chronological and non-overlapping per project
- [ ] Exact same pay-app ranges can be replaced after confirmation, preserving pay-app number
- [ ] Saved pay apps appear in exported Forms history and open a summary/details view
- [ ] Contractor pay apps can be imported from `.xlsx`, `.csv`, or best-effort `.pdf` extraction
- [ ] Contractor comparison matches by item number first, then description fallback, with manual cleanup before compare
- [ ] Contractor comparison produces a standalone PDF discrepancy report
- [ ] Analytics screen shows pay-app-aware summary data, including change since last pay app
- [ ] AppTerminology respected throughout

---

## 2. Data Model

### Unified Export History Layer

The app needs a shared parent export-history model for all exported artifacts. Existing exported types should converge on this model over time.

### New Parent Entity: `ExportArtifact`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | String (UUID) | Yes | Primary key |
| project_id | String | Yes | FK -> projects |
| artifact_type | String | Yes | `entry_pdf`, `form_pdf`, `photo_export`, `pay_application`, `comparison_report` |
| artifact_subtype | String? | No | Form type or specialized subtype where needed |
| source_record_id | String? | No | Optional pointer to source entity |
| title | String | Yes | User-facing artifact label |
| filename | String | Yes | Saved/exported filename |
| local_path | String? | No | Local device path |
| remote_path | String? | No | Supabase storage path |
| mime_type | String | Yes | `application/pdf`, spreadsheet mime type, etc. |
| status | String | Yes | `exported` |
| created_at | DateTime | Yes | |
| updated_at | DateTime | Yes | |
| created_by_user_id | String? | No | |
| deleted_at | DateTime? | No | Soft-delete support |
| deleted_by | String? | No | |

### New Child Entity: `PayApplication`

One `PayApplication` row exists only for saved exported pay apps. It references its export-history parent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | String (UUID) | Yes | Primary key |
| export_artifact_id | String | Yes | FK -> export_artifacts |
| project_id | String | Yes | FK -> projects |
| application_number | int | Yes | Chronological per project, auto-assigned with user override |
| period_start | DateTime | Yes | Start of covered range |
| period_end | DateTime | Yes | End of covered range |
| previous_application_id | String? | No | FK -> pay_applications |
| total_contract_amount | double | Yes | Snapshot at export time |
| total_earned_this_period | double | Yes | Snapshot at export time |
| total_earned_to_date | double | Yes | Snapshot at export time |
| notes | String? | No | Optional export notes |
| created_at | DateTime | Yes | |
| updated_at | DateTime | Yes | |
| created_by_user_id | String? | No | |
| deleted_at | DateTime? | No | |
| deleted_by | String? | No | |

### Optional Temporary Workflow Model: Contractor Comparison

Contractor comparison inputs are not durable by default. The imported contractor artifact itself is not retained. Only the generated discrepancy PDF may be exported.

If implementation needs temporary persisted working state for UI recovery, it should be local-only and ephemeral, not synced.

### Relationships

```text
Project (1) ----< ExportArtifact (many)
   |                  |
   |                  +----< PayApplication (0..1 child for pay_application artifacts)
   |
   +----< BidItem (many)
   |        |
   |        +----< EntryQuantity (many) <---- DailyEntry
   |
   +----< PayApplication (many)
                |
                +---- previous_application_id -> PayApplication
```

### Database Changes
- New parent table: `export_artifacts`
- New child table: `pay_applications`
- Schema version bump (50 -> 51+)
- Change-log triggers on both new tables
- Indexes on all FK columns and `deleted_at`
- Unique constraint on pay-app range identity: one saved pay app per exact `project_id + period_start + period_end`
- Unique constraint on pay-app number within a project

### Sync Considerations
- Add sync adapter config for `export_artifacts`
- Add sync adapter config for `pay_applications`
- `export_artifacts` should be registered before `pay_applications`
- `pay_applications.previous_application_id` is self-referential and must respect pull ordering
- Export files sync through the existing file-sync pipeline via the parent artifact row
- Deleting a pay app deletes:
  - `pay_applications` row
  - `export_artifacts` row
  - local file
  - remote file

---

## 3. Core Rules

### Pay Application Range Rules
- Pay apps are project-scoped and chronological.
- Exact same `project + period_start + period_end` is considered the same pay app identity.
- Exporting the exact same range again prompts the user to replace the saved pay app.
- Replacement reuses the prior pay-app number unless the user overrides it.
- Overlapping non-identical ranges are blocked.
- Users must choose a non-overlapping range to create the next pay app.

### Pay Application Number Rules
- Number is auto-assigned by default.
- User may override the number.
- Number must remain unique within the project.
- Replacement of the exact same saved pay app may reuse the same number.
- Deleted numbers may be reused only through user override or replacement of the exact same saved pay app.

### Saved Pay Application Rules
- Saved pay apps are read-only snapshots in the app.
- Inspectors do not edit exported pay-app contents in-app.
- If data is wrong, they adjust tracked quantities and re-export.
- Saved pay-app status is `exported` for v1.

### Contractor Comparison Rules
- Comparison is launched from a saved pay-app details view.
- Imported contractor files are not retained.
- Comparison does not write back to project data.
- Comparison results are ephemeral unless the user exports the discrepancy PDF.
- If a pay app is compared again later, prompt before replacing the in-session comparison result.

---

## 4. User Flow

### Entry Points

| Feature | Entry Point | Action |
|---------|------------|--------|
| Pay App Export | Pay Items screen -> `Export Pay App` | Date range picker -> number review -> generate `.xlsx` |
| Pay App History | Exported Forms history filtered to Pay Applications | Opens saved pay-app summary/details |
| Contractor Comparison | Saved Pay App detail view -> `Compare Contractor Pay App` | Import/upload -> cleanup -> compare |
| Analytics | Project Dashboard -> 4th quick card | Opens analytics screen |
| Analytics | Pay Items screen -> secondary entry point | Opens same analytics screen |

### Pay Application Export Flow

```text
User taps "Export Pay App"
    ↓
Date Range Picker dialog
  - default start = day after last pay app end
  - default end = today
    ↓
Validation
  - exact same range exists? prompt to replace
  - overlapping different range exists? block
    ↓
Pay-app number review
  - auto-assigned default
  - optional user override
    ↓
Export Orchestrator dispatches to PayAppExcelExporter
    ↓
Generation
  - query entries
  - query bid items
  - compute current and previous totals
  - build G703-style workbook
    ↓
Save/Share dialog (no preview for Excel)
    ↓
Persist ExportArtifact + PayApplication rows
    ↓
Saved pay app appears in exported Forms history
```

### Replace Existing Pay App Flow

```text
User exports a range that exactly matches a saved pay app
    ↓
Confirmation dialog:
  "Replace Pay App #3 for Mar 1 - Mar 15?"
    ↓
On confirm
  - delete prior file references
  - replace saved artifact
  - preserve pay-app number unless user changes it
```

### Saved Pay App Detail Flow

```text
User opens saved pay app from exported Forms history
    ↓
Pay App Summary / Details Screen
  - pay app number
  - project
  - date range
  - status = Exported
  - prior/current totals
  - exported timestamp
    ↓
Available actions
  - Share / Export file
  - Compare Contractor Pay App
  - Delete
```

### Contractor Comparison Flow

```text
User opens saved pay app details
    ↓
Taps "Compare Contractor Pay App"
    ↓
Import source selection
  - .xlsx
  - .csv
  - .pdf (best-effort extraction)
    ↓
Import + parse
  - item number first match
  - description fallback
  - manual cleanup / remap / add / remove rows before compare
    ↓
Comparison result
  - cumulative totals comparison
  - period totals comparison
  - daily discrepancy section only when contractor data includes day-level detail
    ↓
Optional action
  - Export discrepancy report as standalone PDF
```

### Analytics Flow

```text
User opens analytics
    ↓
Analytics screen loads
  - summary header
  - date filter
  - change since last pay app
    ↓
Charts / drill-down
  - progress by item
  - top items by recent activity
  - pay app history comparison
```

---

## 5. UI Components

### New Screens

| Screen | Location | Purpose |
|--------|----------|---------|
| `PayApplicationDetailScreen` | `lib/features/pay_applications/presentation/screens/` | Saved pay-app summary/details plus actions |
| `ProjectAnalyticsScreen` | `lib/features/analytics/presentation/screens/` | Summary header + charts + pay-app-aware metrics |
| `ContractorComparisonScreen` | `lib/features/pay_applications/presentation/screens/` | Import cleanup + discrepancy summary |

### New Dialogs

| Dialog | Purpose |
|--------|---------|
| `PayAppDateRangeDialog` | Date range picker with overlap validation |
| `PayAppReplaceConfirmationDialog` | Confirm replacement of same-range pay app |
| `PayAppNumberDialog` | Review / override auto-assigned pay-app number |
| `ContractorImportSourceDialog` | Select contractor file type/source |
| `ExportSaveShareDialog` | Shared save/share dialog with pluggable preview slot |
| `DeletePayAppDialog` | Confirm deletion of saved pay app and files |

### New Widgets

| Widget | Purpose |
|--------|---------|
| `PayApplicationSummaryCard` | Summary block inside saved pay-app details |
| `ExportArtifactHistoryList` | Filtered exported-artifact history surface |
| `ContractorComparisonSummary` | High-level discrepancy summary |
| `ContractorComparisonTable` | Row-by-row compare table |
| `ManualMatchEditor` | Cleanup/remap UI before compare |
| `AnalyticsSummaryHeader` | Summary header including change since last pay app |
| `PayAppComparisonChart` | Bar chart comparing pay apps |
| `DateRangeFilterBar` | Date filter for analytics |

### Exported Forms History UX

Forms history should behave as exported-artifact history filtered by artifact type. It includes:
- IDR exports
- Form PDF exports
- Photo exports
- Pay applications

Editable saved form responses remain in their existing saved-response surface and are not merged into exported history.

### TestingKeys Required
- `TestingKeys.payAppExportButton`
- `TestingKeys.payAppDateRangePicker`
- `TestingKeys.payAppReplaceConfirmButton`
- `TestingKeys.payAppNumberField`
- `TestingKeys.payAppDetailScreen`
- `TestingKeys.payAppCompareButton`
- `TestingKeys.contractorImportButton`
- `TestingKeys.contractorComparisonScreen`
- `TestingKeys.contractorComparisonExportPdfButton`
- `TestingKeys.analyticsScreen`
- `TestingKeys.analyticsDateFilter`

---

## 6. State Management

### New Providers

**`ExportArtifactProvider`** (ChangeNotifier)

**Responsibilities:**
- Load exported-artifact history by project and type
- Delete exported artifacts and coordinate local/remote file cleanup
- Surface exported Forms history filtered by artifact type

**Key Methods:**
```dart
Future<void> loadForProject(String projectId);
Future<List<ExportArtifact>> getByType(String projectId, String artifactType);
Future<void> deleteArtifact(String artifactId);
```

---

**`PayApplicationProvider`** (ChangeNotifier)

**Responsibilities:**
- Validate date ranges against existing saved pay apps
- Auto-assign next pay-app number
- Support user override with uniqueness validation
- Resolve prior pay app for chaining
- Export pay app through orchestrator
- Replace same-range saved pay app after confirmation

**Key Methods:**
```dart
Future<void> loadForProject(String projectId);
Future<PayAppRangeValidation> validateRange(
  String projectId,
  DateTime start,
  DateTime end,
);
Future<int> getSuggestedNextNumber(String projectId);
Future<PayApplication> exportPayApp({
  required String projectId,
  required DateTime start,
  required DateTime end,
  int? overrideNumber,
  required bool replaceExisting,
});
PayApplication? getLastPayApp(String projectId);
```

---

**`ContractorComparisonProvider`** (ChangeNotifier)

**Responsibilities:**
- Import contractor data from `.xlsx`, `.csv`, or `.pdf`
- Match by item number first, then description fallback
- Support manual cleanup/remap before compare
- Build discrepancy summary
- Export standalone PDF discrepancy report
- Keep working comparison state ephemeral

**Key Methods:**
```dart
Future<void> importContractorArtifact(String payAppId, ImportedFile file);
Future<void> applyManualMatchEdits(List<ManualMatchEdit> edits);
ContractorComparisonResult get result;
Future<ExportResult> exportDiscrepancyPdf();
void clearSession();
```

---

**`ProjectAnalyticsProvider`** (ChangeNotifier)

**Responsibilities:**
- Aggregate summary stats from tracked quantities
- Compute change since last pay app
- Drive pay-app comparison chart
- Support date filtering

**Key Methods:**
```dart
Future<void> loadAnalytics(String projectId);
Future<void> applyDateFilter(DateTime? start, DateTime? end);
AnalyticsSummary get summary;
List<PayAppSummary> get payAppComparison;
double get changeSinceLastPayApp;
```

### Modified Providers

**`EntryQuantityProvider`** — add:
```dart
Future<Map<String, double>> getQuantitiesByDateRange(
  String projectId,
  DateTime start,
  DateTime end,
);
```

### Data Flow

```text
Pay App Export
  -> PayApplicationProvider
  -> ExportOrchestratorProvider
  -> PayAppExcelExporter
  -> ExportArtifact + PayApplication persist

Saved Pay App Detail
  -> ExportArtifactProvider + PayApplicationProvider

Contractor Comparison
  -> ContractorComparisonProvider
  -> import parser / extraction
  -> discrepancy PDF exporter

Analytics
  -> ProjectAnalyticsProvider
  -> BidItemRepository + EntryQuantityRepository + PayApplicationRepository
```

### Error Handling
- Same-range replace requires explicit confirmation
- Overlapping non-identical ranges block export
- Duplicate pay-app numbers block save
- Contractor import parse errors route to manual cleanup flow when possible
- Failed discrepancy PDF export surfaces as normal export error

---

## 7. Offline Behavior

### Offline Capabilities

| Action | Offline? | Notes |
|--------|----------|-------|
| Export pay app | Yes | Based on local tracked data |
| Replace same-range pay app | Yes | Local replace first, sync later |
| View saved pay app details | Yes | Local artifact metadata |
| Delete saved pay app | Yes | Local delete first, sync later |
| Import contractor pay app | Yes | Local parsing only |
| Run contractor comparison | Yes | Local compare only |
| Export discrepancy PDF | Yes | Local PDF generation |
| View analytics | Yes | Local aggregation |

### Sync Strategy

| Entity | Direction | Adapter Type |
|--------|-----------|-------------|
| export_artifacts | Bidirectional | Data-driven AdapterConfig or dedicated file-aware adapter |
| pay_applications | Bidirectional | Data-driven AdapterConfig |

### File Sync
- Pay-app `.xlsx` files sync through the parent `export_artifacts` row
- Discrepancy PDFs, if exported, also sync through `export_artifacts`
- Imported contractor files do not persist and do not sync

---

## 8. Edge Cases

### Error States

| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| No bid items in project | Block pay-app export | "Add pay items before creating a pay application" |
| No entries in date range | Allow export | Warning that values will be zero |
| Exact same range already exists | Prompt replace | "Replace Pay App #N for this date range?" |
| Range overlaps different saved pay app | Block | "Pay application ranges cannot overlap" |
| User overrides pay-app number with existing number | Block | "Pay application number already exists in this project" |
| Contractor import missing some item numbers | Fallback to description match, then manual cleanup | "Some items need review before comparison" |
| Contractor artifact only has cumulative totals | Compare totals only | No daily discrepancy section |
| Contractor artifact includes day detail | Compare totals + daily discrepancies | Daily discrepancy section enabled |
| Best-effort PDF extraction partially fails | Route to manual cleanup | "Review imported rows before comparing" |

### Data Integrity
- Saved pay apps are snapshots.
- Saved pay apps are not edited in-app after export.
- Imported contractor artifacts are ephemeral and not retained.
- Discrepancy reports are standalone exports and not child records of the pay app.

---

## 9. Testing Strategy

### Unit Tests

| Component | Test Focus | Priority |
|-----------|-----------|----------|
| PayApplicationRepository | exact-range identity, overlap blocking, chronological number rules | HIGH |
| PayApplicationProvider | replace flow, number override validation, chaining | HIGH |
| ExportArtifactRepository | type filtering, delete behavior, history loading | HIGH |
| PayAppExcelExporter | correct G703 layout, chaining totals, range aggregation | HIGH |
| ContractorComparisonProvider | import parsing, item-number match, description fallback, manual cleanup | HIGH |
| Contractor discrepancy builder | cumulative totals, period totals, optional daily section | HIGH |
| ProjectAnalyticsProvider | change since last pay app, pay-app comparison chart data | HIGH |
| ExportOrchestrator | parent artifact creation and correct exporter dispatch | MED |

### Widget Tests

| Screen/Widget | Test Focus | Priority |
|--------------|-----------|----------|
| PayAppDateRangeDialog | overlap validation, same-range replace prompt | HIGH |
| PayApplicationDetailScreen | summary rendering + action availability | HIGH |
| ExportArtifactHistoryList | exported-form filtering by artifact type | HIGH |
| ContractorComparisonScreen | import cleanup and discrepancy summary | HIGH |
| ManualMatchEditor | remap/add/remove before compare | MED |
| ProjectAnalyticsScreen | change since last pay app + chart rendering | MED |
| ExportSaveShareDialog | Excel has no preview slot, PDF does | MED |

### Integration Tests

- [ ] Export pay app with tracked quantities across multiple days and verify `.xlsx` content
- [ ] Export same exact range twice and verify replace-confirm flow preserves pay-app number
- [ ] Attempt overlapping non-identical pay-app range and verify block
- [ ] Override pay-app number and verify uniqueness enforcement
- [ ] Saved pay app appears in exported Forms history and opens details screen
- [ ] Delete saved pay app and verify row + local file + remote file removal
- [ ] Import contractor `.xlsx` and generate discrepancy PDF
- [ ] Import contractor `.csv` and generate discrepancy PDF
- [ ] Import contractor `.pdf` via best-effort extraction and manual cleanup
- [ ] Comparison with totals-only contractor data omits daily discrepancy section
- [ ] Comparison with daily-detail contractor data includes daily discrepancy section
- [ ] Analytics screen computes change since last pay app correctly

### Test Flow / Skill Updates Required

This spec must update the maintained test system, not only local test cases.

Required doc updates:
- `.codex/skills/test.md`
- `.claude/skills/test/SKILL.md`
- `.claude/test-flows/flow-dependencies.md`
- `.claude/test-flows/tiers/toolbox-and-pdf.md`
- add or update a pay-app/export tier doc
- add sync/export verification coverage for saved pay-app artifacts and delete propagation

Suggested new flow coverage:
- exported-artifact history visibility
- same-range replace flow
- overlap-block flow
- pay-app delete propagation
- contractor comparison import + discrepancy PDF export

---

## 10. Performance Considerations

### Potential Bottlenecks

| Area | Concern | Mitigation |
|------|---------|------------|
| Excel generation | Large range x many bid items | Batch SQL + isolate generation |
| Contractor PDF import | OCR/table extraction cost | Reuse existing bid-item extraction patterns and manual cleanup path |
| Exported history screen | Mixed artifact loading | Filter in query by type/project |
| Analytics | Pay-app-aware aggregation | Cache summary and recompute on filter change |

### Targets
- Pay-app export: <3 seconds for 90-day x 40-item range
- Contractor comparison import: best-effort parse within a few seconds for standard contractor sheets
- Analytics initial load: <500ms on normal project size

---

## 11. Security Implications

### Authentication & Authorization

| Operation | Auth Required | Write Guard |
|-----------|--------------|-------------|
| View exported pay apps | Yes | Read-only |
| Export pay app | Yes | `canEditFieldData` |
| Delete saved pay app | Yes | `canEditFieldData` |
| Import contractor pay app | Yes | `canEditFieldData` |
| Export discrepancy PDF | Yes | `canEditFieldData` |
| View analytics | Yes | Read-only |

### Data Exposure

| Data | Sensitivity | Protection |
|------|------------|------------|
| Pay-app `.xlsx` files | Business-sensitive | App sandbox + company-scoped storage |
| Discrepancy PDFs | Business-sensitive | App sandbox + company-scoped storage |
| Imported contractor files | Temporary | Do not retain after compare session |
| Aggregated analytics | Business-sensitive | Computed on-device from secured data |

### RLS Policies
- `export_artifacts` and `pay_applications` are scoped by project/company
- file storage paths remain company-scoped

---

## 12. Migration / Cleanup

### Schema Changes

| Table | Change | Strategy |
|-------|--------|---------|
| `export_artifacts` | NEW | Schema v51 |
| `pay_applications` | NEW | Schema v51 |

### Export System Refactor

Current fragmented export history should converge toward the parent artifact model:

| Current | Target |
|---------|--------|
| `entry_exports` | parent `export_artifacts` + entry-specific source linkage |
| `form_exports` | parent `export_artifacts` + form-specific source linkage |
| pay app history | parent `export_artifacts` + `pay_applications` child |
| discrepancy report export | parent `export_artifacts` with `comparison_report` artifact type |

### Files Affected
1. `lib/core/database/database_service.dart`
2. `lib/core/database/schema/`
3. `lib/core/database/schema_verifier.dart`
4. `test/core/database/schema_verifier_test.dart`
5. `test/core/database/database_service_test.dart`
6. export history / orchestrator layers
7. Forms exported-history UI
8. pay-app feature module
9. contractor comparison flow

### Backward Compatibility
- Existing exported artifact history should continue to display prior export types
- Editable saved form responses remain separate
- No contractor comparison data is persisted unless the user exports a discrepancy PDF
