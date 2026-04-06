# Source Excerpts — By Concern

## Concern 1: Unified Export History Layer (Data Model + Schema)

### Existing export models to converge on

**EntryExport** (`lib/features/entries/data/models/entry_export.dart:4-103`):
Fields: id, entryId, projectId, filePath, remotePath, filename, fileSizeBytes, exportedAt, createdAt, updatedAt, createdByUserId, deletedAt, deletedBy.

**FormExport** (`lib/features/forms/data/models/form_export.dart:8-119`):
Fields: id, formResponseId, projectId, entryId, filePath, remotePath, filename, formType, fileSizeBytes, exportedAt, createdAt, updatedAt, createdByUserId, deletedAt, deletedBy.

### New ExportArtifact model should include
Superset of both: id, projectId, artifactType, artifactSubtype, sourceRecordId, title, filename, localPath, remotePath, mimeType, status, createdAt, updatedAt, createdByUserId, deletedAt, deletedBy.

### Schema template (follow EntryExportTables pattern)
```dart
class ExportArtifactTables {
  static const String createExportArtifactsTable = '''
    CREATE TABLE IF NOT EXISTS export_artifacts (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      artifact_type TEXT NOT NULL,
      artifact_subtype TEXT,
      source_record_id TEXT,
      title TEXT NOT NULL,
      filename TEXT NOT NULL,
      local_path TEXT,
      remote_path TEXT,
      mime_type TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'exported',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';

  static const String createPayApplicationsTable = '''
    CREATE TABLE IF NOT EXISTS pay_applications (
      id TEXT PRIMARY KEY,
      export_artifact_id TEXT NOT NULL,
      project_id TEXT NOT NULL,
      application_number INTEGER NOT NULL,
      period_start TEXT NOT NULL,
      period_end TEXT NOT NULL,
      previous_application_id TEXT,
      total_contract_amount REAL NOT NULL,
      total_earned_this_period REAL NOT NULL,
      total_earned_to_date REAL NOT NULL,
      notes TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (export_artifact_id) REFERENCES export_artifacts(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY (previous_application_id) REFERENCES pay_applications(id) ON DELETE SET NULL
    )
  ''';
}
```

## Concern 2: Pay Application Export (Provider + Use Case)

### Closest existing analog: EntryExportProvider
`lib/features/entries/presentation/providers/entry_export_provider.dart:11-91`:
- Wraps `ExportEntryUseCase`, holds `_isExporting`, `_exportedPaths`, `_errorMessage`, `_exportHistory`
- `exportAllFormsForEntry()` — try/catch/finally with notifyListeners
- `loadExportHistory(projectId)` — loads history by project

### Closest existing analog: FormExportProvider
`lib/features/forms/presentation/providers/form_export_provider.dart:8`:
- Wraps `ExportFormUseCase`, holds `_isExporting`, `_errorMessage`, `_exportHistory`, `_isLoadingHistory`
- `exportFormToPdf()`, `loadProjectExportHistory()`, `loadResponseExportHistory()`

### Data for pay app export computation
**BidItem fields for G703**: itemNumber, description, unit, bidQuantity, unitPrice, bidAmount
**EntryQuantity fields**: entryId (links to date), bidItemId, quantity, notes

## Concern 3: Sync Registration

### Current adapter order (sync_registry.dart:31-54)
Position 47: `form_exports` (simple adapter)
Position 48: `entry_exports` (simple adapter)

### New adapters should be inserted
```dart
// In registerSyncAdapters(), after form_exports and before entry_exports:
simpleByTable['export_artifacts']!,   // NEW: parent for all exported artifacts
simpleByTable['pay_applications']!,   // NEW: child of export_artifacts
```

### AdapterConfig templates
```dart
// export_artifacts — file-aware, project-scoped
AdapterConfig(
  table: 'export_artifacts',
  scope: ScopeType.viaProject,
  fkDeps: ['projects'],
  fkColumnMap: {'projects': 'project_id'},
  localOnlyColumns: ['local_path'],
  isFileAdapter: true,
  storageBucket: 'export-artifacts',
  buildStoragePath: _buildExportArtifactPath,
  extractRecordName: _extractExportRecordName,
),

// pay_applications — data-only, project-scoped
AdapterConfig(
  table: 'pay_applications',
  scope: ScopeType.viaProject,
  fkDeps: ['export_artifacts', 'projects'],
  fkColumnMap: {
    'export_artifacts': 'export_artifact_id',
    'projects': 'project_id',
  },
),
```

### Trigger registration
Add to `triggeredTables`: `'export_artifacts'`, `'pay_applications'`
Add to `tablesWithDirectProjectId`: `'export_artifacts'`, `'pay_applications'`

## Concern 4: Dashboard Analytics Entry Point

### Current dashboard quick cards (`project_dashboard_screen.dart:320-366`)
3 cards in a Row with Expanded children: Entries, Pay Items, Toolbox.
Uses `Consumer2<DailyEntryProvider, BidItemProvider>`.

### Adding 4th card
Add another `Expanded` child with `DashboardStatCard(label: 'Analytics', icon: Icons.analytics_outlined, ...)` and `onTap: () => context.push('/analytics/$projectId')`.

## Concern 5: Contractor Comparison (new feature, no existing analog)

### File import parsing — closest existing pattern
`lib/features/pdf/services/extraction/` — existing OCR/table extraction pipeline. Can reuse patterns for best-effort PDF parsing.
`lib/features/quantities/utils/budget_sanity_checker.dart` — existing bid item validation logic.

### Item matching by item number
`BidItemRepository.getByItemNumber(String projectId, String itemNumber)` — exact match on item_number column. Usable for contractor data matching.

## Concern 6: AppTerminology Respect

### Current terms to use throughout pay app UI
```dart
AppTerminology.bidItem      // "Bid Item" or "Pay Item"
AppTerminology.bidItemPlural // "Bid Items" or "Pay Items"
AppTerminology.dailyReport  // "Inspector's Daily Report" or "Daily Work Report"
AppTerminology.dailyReportShort // "IDR" or "DWR"
```

### Pay app-specific terms (not in AppTerminology yet)
May need to add: `payApplication` -> "Pay Application" (both modes).
