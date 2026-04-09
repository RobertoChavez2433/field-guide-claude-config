# CodeMunch Architecture Audit — Pre-Production Cleanup (Verified)

**Date:** 2026-04-04
**Tool:** CodeMunch MCP (static import graph + PageRank analysis)
**Scope:** Full `lib/` codebase
**Index:** 1,287 Dart files | 9,694 symbols | 793 files in `lib/`, 367 in `test/`
**Verification:** Two independent agents verified dead code false positives and god class method counts

---

## Executive Summary

The codebase has **4 classes warranting splits** (not 13 as initially flagged — CodeMunch counted getters as methods, inflating counts by 40-50%), **16 genuinely dead remote datasource files** (the sync adapter pattern superseded them), and **8 high-centrality architectural hotspots**. The top priorities are splitting `SyncEngine` (37 methods, 2,374 lines) and `AuthProvider` (30 methods, 5 distinct responsibilities), plus deleting ~19 confirmed-dead files.

---

## 1. GOD CLASSES — Verified Method Counts

**IMPORTANT:** CodeMunch counted Dart getters as methods, inflating all provider counts by 40-50%. The table below shows **verified actual method counts** (methods only) alongside the raw CodeMunch count (methods + getters).

### Warranting Split (verified)

| Class | File | Actual Methods | With Getters | Lines | Split Justified? |
|-------|------|---------------|-------------|-------|-----------------|
| **SyncEngine** | `lib/features/sync/engine/sync_engine.dart` | 37 | 37 | 2,374 | **Strongest candidate** — push/pull/maintenance clearly separable |
| **AuthProvider** | `lib/features/auth/presentation/providers/auth_provider.dart` | 30 | 49 | 867 | **Yes** — mock auth, permissions, password recovery, profile are 4+ responsibilities |
| **FormPdfService** | `lib/features/forms/data/services/form_pdf_service.dart` | 25 | 25 | 1,224 | **Yes** — field resolution, table filling, file output, cache separable |
| **ProjectProvider** | `lib/features/projects/presentation/providers/project_provider.dart` | 33 | 55 | 797 | **Moderate** — enrollment + filter state extractable |

### Borderline (may not need splitting)

| Class | File | Actual Methods | With Getters | Lines | Notes |
|-------|------|---------------|-------------|-------|-------|
| DailyEntryProvider | `lib/features/entries/presentation/providers/daily_entry_provider.dart` | 25 | 41 | 561 | Pagination/filtering as mixins would be clean but not urgent |
| _HomeScreenState | `lib/features/entries/presentation/screens/home_screen.dart` | 35 | — | — | Calendar logic could move to controller |
| _ProjectSetupScreenState | `lib/features/projects/presentation/screens/project_setup_screen.dart` | 34 | — | — | Wizard step logic could move to controller |
| EntryEditingController | `lib/features/entries/presentation/controllers/entry_editing_controller.dart` | 34 | — | — | Already a controller, responsibilities are cohesive |

### Do NOT Split (verified too small)

| Class | File | Actual Methods | With Getters | Notes |
|-------|------|---------------|-------------|-------|
| SyncProvider | `lib/features/sync/presentation/providers/sync_provider.dart` | 17 | 32 | Thin delegation layer, appropriately sized |
| BidItemProvider | `lib/features/quantities/presentation/providers/bid_item_provider.dart` | 16 | 29 | Thin layer over BaseListProvider |

---

## 2. RECOMMENDED SPLITS (Verified)

### SyncEngine (37 methods, 2,374 lines) — HIGHEST PRIORITY

The largest file in the codebase with the clearest separation boundaries.

**Proposed split:**
- **SyncPushHandler** (~14 methods): `_push`, `_routeAndPush`, `_pushUpsert`, `_pushDelete`, `_pushFileThreePhase`, `_validateStoragePath`, `_stripExifGps`, `_preCheckUniqueConstraint`, `_childFkColumns`, `validateAndStampCompanyId`, `_handlePushError`, `_computeBackoff`, `_handleAuthError`
- **SyncPullHandler** (~11 methods): `_pull`, `_pullTable`, `_applyScopeFilter`, `_loadSyncedProjectIds`, `_reconcileSyncedProjects`, `_enrollProjectsFromAssignments`, `_loadContractorIdsForProjectIds`, `_rescueParentProject`, `_getLocalColumns`, `_stripUnknownColumns`, `_createDeletionNotification`
- **SyncMaintenanceRunner** (~5 methods): `_runMaintenanceHousekeeping`, `_cleanupExpiredConflicts`, `_storeIntegrityResult`, `_storeMetadata`, `_clearCursor`
- **SyncEngine** (slim orchestrator): `pushAndPull`, `pushOnly`, `pullOnly`, `resetState`, `createForBackgroundSync`, `_postSyncStatus`

### AuthProvider (30 methods) — HIGH PRIORITY

**Proposed split:**
- **AuthStateProvider**: `signUp`, `signIn`, `signOut`, `signOutLocally`, `forceReauthOnly`, `handleForceReauth`, `updateLastActive`, `checkInactivityTimeout`, `_clearSecureStorageOnSignOut`
- **UserProfileProvider**: `loadUserProfile`, `updateProfile`, `refreshUserProfile`, `updateGaugeNumber`, `updateInitials`, `setUserProfile`
- **AuthFlowProvider**: `resetPassword`, `verifyRecoveryOtp`, `updatePassword`, `completePasswordRecovery`, `_parseOtpError`
- **MockAuthProvider** (or mixin): `_initMockAuth`, `_mockSignUp`, `_mockSignIn`, `_mockSignOut`, `_mockResetPassword`
- **Permission getters** could become a `PermissionChecker` value object: `isAdmin`, `isEngineer`, `isInspector`, `canManageProjects`, `canEditFieldData`, `canDeleteProject`, `canEditEntry`

**WARNING:** AuthProvider has 57 dependents (in-degree). This refactor has the highest blast radius. Plan import migration for 57 consumers.

### FormPdfService (25 methods, 1,224 lines) — MODERATE PRIORITY

**Proposed split:**
- **FormPdfService** (keep, slim): `generatePreviewPdf`, `generateFormPdf`, `generateFilledPdf`, `generateDebugPdf`, `generateFilename`
- **PdfFieldResolver**: `_generateFieldNameVariations`, `_getMdotFieldPatterns`, `_trySetField`, `_setField`, `_setFieldByType`, `_parseCheckboxValue`, `_sanitizeForPdf`
- **PdfTableRowFiller**: `_fillTableRowFields`, `_buildGroupColumnMap`, `_generateRowFieldVariations`
- **PdfFileOutputService**: `savePdfWithPicker`, `saveTempPdf`, `previewPdf`, `sharePdf`

### ProjectProvider (33 methods) — LOWER PRIORITY

**Proposed split (moderate justification):**
- Extract **enrollment** (`enrollProject`, `unenrollProject`) to a `ProjectEnrollmentService`
- Extract **filter/search state** (`setTabIndex`, `setCompanyFilter`, `setSearchQuery`, `clearSearch`, `_buildMergedView`) to a `ProjectFilterProvider`
- Keep CRUD + selection in `ProjectProvider`

---

## 3. CONFIRMED DEAD CODE — Safe to Delete

Verified by agent with grep evidence. These files/symbols have zero consumers.

### 3.1 Remote Datasources (16 files) — CONFIRMED DEAD

The sync engine uses `TableAdapter` subclasses that talk to Supabase directly, NOT through these remote datasource classes. These were scaffolding for a datasource-per-table pattern that was superseded by the sync adapter pattern.

| File | Class |
|------|-------|
| `lib/features/entries/data/datasources/remote/daily_entry_remote_datasource.dart` | DailyEntryRemoteDatasource |
| `lib/features/entries/data/datasources/remote/document_remote_datasource.dart` | DocumentRemoteDatasource |
| `lib/features/entries/data/datasources/remote/entry_export_remote_datasource.dart` | EntryExportRemoteDatasource |
| `lib/features/contractors/data/datasources/remote/contractor_remote_datasource.dart` | ContractorRemoteDatasource |
| `lib/features/contractors/data/datasources/remote/equipment_remote_datasource.dart` | EquipmentRemoteDatasource |
| `lib/features/contractors/data/datasources/remote/entry_equipment_remote_datasource.dart` | EntryEquipmentRemoteDatasource |
| `lib/features/contractors/data/datasources/remote/personnel_type_remote_datasource.dart` | PersonnelTypeRemoteDatasource |
| `lib/features/photos/data/datasources/remote/photo_remote_datasource.dart` | PhotoRemoteDatasource |
| `lib/features/quantities/data/datasources/remote/bid_item_remote_datasource.dart` | BidItemRemoteDatasource |
| `lib/features/quantities/data/datasources/remote/entry_quantity_remote_datasource.dart` | EntryQuantityRemoteDatasource |
| `lib/features/todos/data/datasources/remote/todo_item_remote_datasource.dart` | TodoItemRemoteDatasource |
| `lib/features/forms/data/datasources/remote/form_response_remote_datasource.dart` | FormResponseRemoteDatasource |
| `lib/features/forms/data/datasources/remote/inspector_form_remote_datasource.dart` | InspectorFormRemoteDatasource |
| `lib/features/forms/data/datasources/remote/form_export_remote_datasource.dart` | FormExportRemoteDatasource |
| `lib/features/calculator/data/datasources/remote/calculation_history_remote_datasource.dart` | CalculationHistoryRemoteDatasource |
| `lib/features/locations/data/datasources/remote/location_remote_datasource.dart` | LocationRemoteDatasource |

**NOT dead (confirmed used):**
- `UserProfileRemoteDatasource` — Constructed in `auth_initializer.dart:49`
- `ProjectRemoteDatasource` — Constructed in `project_initializer.dart:52`

### 3.2 Provider Infrastructure (1 file) — CONFIRMED DEAD

| File | Class | Notes |
|------|-------|-------|
| `lib/shared/providers/paged_list_provider.dart` | PagedListProvider | Zero subclasses. `extends PagedListProvider` has zero matches. Created as infrastructure but never consumed. |

**NOT dead:** `BaseListProvider` has 5 active subclasses (LocationProvider, PersonnelTypeProvider, ContractorProvider, BidItemProvider, DailyEntryProvider).

### 3.3 Time Provider (1 file, 5 classes) — CONFIRMED DEAD

| File | Classes | Notes |
|------|---------|-------|
| `lib/shared/time_provider.dart` | TimeProvider, RealTimeProvider, FixedTimeProvider, AppTime, _TestModeTimeProvider | `AppTime.now()`, `AppTime.today()`, `AppTime.setProvider()` are never called anywhere. Exported via `shared.dart` barrel but never consumed. |

### 3.4 UI State Models (1 file, 2 classes) — CONFIRMED DEAD

| File | Classes | Notes |
|------|---------|-------|
| `lib/features/entries/presentation/models/contractor_ui_state.dart` | ContractorUIState, EquipmentUIState | Zero references outside file. Superseded by `ContractorEditingController`. Also remove barrel entry in `models.dart`. |

### Dead Code Deletion Summary

| Category | Files | Estimated Lines Removed |
|----------|-------|------------------------|
| Remote datasources | 16 | ~2,500 |
| PagedListProvider | 1 | ~300 |
| time_provider.dart | 1 | ~150 |
| contractor_ui_state.dart | 1 | ~100 |
| **Total** | **19 files** | **~3,050 lines** |

---

## 4. DESIGN SYSTEM COMPONENTS — Pending Adoption (NOT Dead)

These 3 components were flagged as dead but are **design system consolidation components** built to replace scattered ad-hoc patterns. They have zero current consumers but exist intentionally for consistency enforcement.

| Component | File | Purpose | What It Replaces |
|-----------|------|---------|-----------------|
| **AppBottomBar** | `lib/core/design_system/app_bottom_bar.dart` | Frosted-glass sticky action bar with blur backdrop + SafeArea | 12+ manual SafeArea + Container + BackdropFilter patterns across screens |
| **AppPhotoGrid** | `lib/core/design_system/app_photo_grid.dart` | Reusable photo thumbnail grid with add-photo button | Ad-hoc GridView photo grids on 4+ screens (entry editor, gallery, forms) |
| **AppStickyHeader** | `lib/core/design_system/app_sticky_header.dart` | SliverPersistentHeaderDelegate wrapper with blur | 50+ lines of boilerplate per sticky header in CustomScrollViews |

**Action:** Do NOT delete. These should be adopted during UI polish passes to consolidate duplicated patterns.

---

## 5. CONFIRMED FALSE POSITIVES — Do NOT Delete

The following categories were originally flagged as dead but are **confirmed used at runtime**:

| Category | Count | Why Flagged | Why Actually Used |
|----------|-------|-------------|-------------------|
| Screen/Widget classes | ~120 classes | No static imports | Referenced via GoRouter route definitions (all 20 checked screens confirmed) |
| Schema table classes | 15 classes | No static imports | Called from `DatabaseService._onCreate`/`_onUpgrade` |
| Testing keys | 16 classes | Test-only references excluded | Used in 104 production files for widget key assignments |
| BaseListProvider | 1 class | Zero importers in graph | 5 active subclasses inherit its methods |
| PdfService | 1 class | Flagged as dead | Used for entry report PDF generation (distinct from extraction pipeline) |
| GridLineColumnDetector | 1 class | Flagged as dead | Used as field in `ColumnDetectorV2` (extraction pipeline stage) |
| 6 design system widgets | 6 classes | No direct imports | Used across screens via barrel export (AppBudgetWarningChip, AppIcon, AppLoadingState, AppProgressBar, AppSectionCard, AppSectionHeader) |
| 3 design system widgets | 3 classes | No consumers | Pending adoption, not dead (AppBottomBar, AppPhotoGrid, AppStickyHeader) |
| 2 remote datasources | 2 classes | — | UserProfileRemoteDatasource + ProjectRemoteDatasource are DI-registered |

---

## 6. ARCHITECTURAL HOTSPOTS — PageRank Analysis

Symbols ranked by PageRank centrality (how much of the codebase depends on them):

### Tier 1: Very High Risk (100+ dependents)

| Symbol | PageRank | In-Degree | Type | Risk Profile |
|--------|----------|-----------|------|-------------|
| Logger | 0.0598 | 202 files | class | Imported by everything. Any API change is catastrophic. Stable. |
| DatabaseService | 0.0138 | 110 files | class | Schema backbone. High blast radius but rarely changes API. |
| DesignConstants | 0.0118 | 103 files | class | UI constants. Changes ripple to all screens. |
| design_system.dart (barrel) | — | 95 files | barrel | Barrel export for 24 design system components |
| FieldGuideColors | 0.0090 | 88 files | class | Color definitions. Theme-level changes only. |

### Tier 2: High Risk (40-99 dependents)

| Symbol | PageRank | In-Degree | Type | Risk Profile |
|--------|----------|-----------|------|-------------|
| AuthProvider | 0.0037 | 57 files | class | **Split candidate + high centrality** — most dangerous refactor |
| BaseRepository | 0.0094 | 51 files | class | Base class for all repositories. API stable. |
| ScopeType | 0.0104 | 44 files | enum | Sync scope enum. Used in all adapters. |
| DailyEntry (model) | 0.0052 | 43 files | class | Core domain model. Field additions ripple. |

### Tier 3: Medium Risk (20-39 dependents)

| Symbol | PageRank | In-Degree | Type |
|--------|----------|-----------|------|
| SyncOrchestrator | 0.0025 | 30 files | class |
| BidItem | 0.0041 | 29 files | class |
| AppTheme | 0.0048 | 29 files | class |
| TableAdapter | 0.0062 | 28 files | class |
| SyncResult | 0.0030 | 29 files | class |
| PagedResult | 0.0151 | 27 files | class |
| FormResponse | 0.0036 | 25 files | class |
| Photo | 0.0030 | 25 files | class |

### Key Risk Intersection

**AuthProvider** is the only symbol that is both a split candidate (30 methods, 5 responsibilities) AND a high-centrality node (57 dependents). Refactoring it requires careful import migration across 57 files.

---

## 7. PDF EXTRACTION SUBSYSTEM — Accumulated Debt

The `lib/features/pdf/services/extraction/` directory has the highest concentration of potentially dead code (~200+ symbols across 25+ files). While much of this needs manual review per-method, the patterns are:

- **Unused constants** in `grid_line_remover.dart` (9 constants)
- **Standalone helper functions** in `grid_line_detector.dart` (10 functions), `grid_line_remover.dart` (6 functions) — likely leftovers from pipeline iterations
- **Model getter bloat** in `detected_regions.dart` (25 unused methods), `processed_items.dart` (16 unused methods), `extraction_result.dart` (13 unused methods) — computed properties that were never consumed

**Recommendation:** Audit which getters/methods are actually called from the active pipeline stages. Remove unused ones.

---

## 8. PRIORITIZED ACTION ITEMS

### P0 — Pre-Launch (highest ROI)

1. **Delete 19 confirmed-dead files** (~3,050 lines removed) — Zero risk, immediate hygiene win
   - 16 remote datasource files
   - PagedListProvider
   - time_provider.dart
   - contractor_ui_state.dart
2. **Split SyncEngine** (37 methods, 2,374 lines) — Clearest separation boundaries, isolated to sync feature
3. **Split AuthProvider** (30 methods, 57 dependents) — Highest risk/reward. Plan import migration for 57 consumers.

### P1 — Pre-Launch (if time permits)

4. **Split FormPdfService** (25 methods, 1,224 lines) — Field resolution + table filling + file output
5. **Extract HomeScreen/ProjectSetupScreen logic** (35/34 methods in State) to controllers
6. **Split ProjectProvider** (33 methods) — Moderate justification, enrollment + filter extractable

### P2 — Post-Launch / UI Polish

7. **Adopt design system consolidation components** — Migrate screens to use AppBottomBar, AppPhotoGrid, AppStickyHeader instead of ad-hoc patterns
8. **Clean PDF extraction dead code** (~200 symbols) — Per-method audit of getters in model classes
9. **Audit BaseListProvider** — Verify which of its ~15 methods are actually called by all 5 subclasses
10. **Extract remaining screen State logic** (FormViewer, Todos, Gallery)

---

## 9. METHODOLOGY & CAVEATS

### Tools Used
- **CodeMunch `index_folder`** — Local incremental indexing with AI summaries
- **CodeMunch `get_repo_outline`** — Directory/language/import overview
- **CodeMunch `find_dead_code`** — Static import graph dead code detection (min confidence 0.8)
- **CodeMunch `get_symbol_importance`** — PageRank centrality ranking (top 50)
- **CodeMunch `search_symbols`** — Class discovery sorted by centrality
- **CodeMunch `get_file_outline`** — Per-file class/method inventory (batch queries)

### Verification Agents
- **Dead code false positive verifier** — Grep-verified all 6 categories (screens in routes, datasources in DI, schema in DatabaseService, design system usage, testing keys in tests, genuinely suspicious dead code). 119 tool calls.
- **God class method count verifier** — Read each of 7 flagged files, counted actual public/private methods vs getters, identified responsibility groups. 31 tool calls.

### Known Limitations
1. **Getter inflation** — CodeMunch counts Dart getters as methods. All provider "method counts" in raw output are inflated by 40-50%. This report uses verified counts.
2. **Flutter route references not traced** — Screens referenced via GoRouter are flagged as dead (confirmed false positive)
3. **Provider DI registration not traced** — Classes registered in AppProviders/AppDependencies are flagged (mixed — some are genuinely dead, some are used)
4. **Barrel exports partially traced** — Barrel-exported but unconsumed symbols (like time_provider.dart) appear connected but are actually dead
5. **Test file references excluded** — By design. Testing keys appear dead but are used in 104 production files.
6. **Design system "pending adoption" pattern** — Components intentionally built but not yet adopted register as dead in static analysis

### Confidence Levels
- God class identification: **HIGH** — Verified by reading actual files
- Dead code (confirmed dead): **HIGH** — Grep-verified zero consumers
- Dead code (PDF extraction): **MEDIUM** — Needs per-method manual review
- PageRank centrality: **HIGH** — Based on actual import graph
- Recommended splits: **HIGH** — Verified responsibility groups from actual method analysis
