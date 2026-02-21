# Master Refactoring Catalog -- Field Guide App

**Date**: 2026-02-20
**Sources**: 4 parallel code-review agents + fresh flutter_prunekit scan + prior reviews (2026-02-14, 2026-02-16)
**Status**: REVIEW DRAFT -- for prioritization and plan creation

---

## Executive Summary

The Field Guide App has a solid architectural foundation (feature-first Clean Architecture, base abstractions, barrel exports, offline-first SQLite+Supabase). However, organic growth across 30+ development sessions has accumulated significant structural debt:

| Category | Scope | Est. Lines Addressable |
|----------|-------|----------------------|
| God classes (screens >1,500 lines) | 7 files, 14,900+ lines combined | ~4,500 saveable via extraction |
| Dead code (confirmed deletable) | 15 unused classes, 1 dead file (951 lines), 440 lines hardcoded fallback | ~1,600 lines deletable |
| DRY violations (duplicated logic) | 11 identical repos, 32 sync methods, 3x entry screens, toolbox duplication | ~2,800 lines consolidatable |
| Architecture debt (DI violations, service locator, stalled migration) | main.dart (624 lines), dual sync arch, 15 raw providers | ~1,500 lines restructurable |
| Crash risks | 1 confirmed (firstWhere), 13 lower-risk | 1 critical, 13 medium |
| Unused methods (prunekit) | 579 flagged (~15-20% true positives) | ~80-115 truly dead methods |
| Write-only fields (prunekit) | 42 flagged | Verification needed |

**Total estimated addressable debt: ~10,400+ lines** across a ~56,000 line codebase (18.5%).

---

## Codebase Health Snapshot (flutter_prunekit 2026-02-20)

| Category | Total | Unused/Flagged | Usage Rate |
|----------|-------|----------------|------------|
| Files analyzed | 448 | -- | -- |
| Classes/Types | 556 | 15 unused | 97.3% |
| Methods | 3,078 | 579 unused | 81.2% |
| Variables | 8,389 | 36 unused | 99.6% |
| Fields | 3,124 | 90 unused + 42 write-only | 97.1% |
| Analysis time | 19.3s | -- | -- |

**Warning**: 122 files use dynamic types -- prunekit may have false negatives in those files.

### Confirmed Unused Classes (15)

| Class | File | Notes |
|-------|------|-------|
| `ConfigurationException` | `core/config/config_validator.dart:96` | |
| `ContractorSummaryWidget` | `entries/.../contractor_editor_widget.dart:384` | |
| `InterpretationPatterns` | `pdf/.../rules/interpretation_patterns.dart:1` | |
| `RowClassifierV2` | `pdf/.../stages/row_classifier_v2.dart:19` | Entire 951-line file is dead |
| `SyncOrchestrator` | `sync/application/sync_orchestrator.dart:13` | Built but never wired in |
| `DensityCalculatorService` | `toolbox/.../density_calculator_service.dart:99` | |
| `BatchOperationsMixin` | `shared/datasources/query_mixins.dart:3` | |
| `SyncStatusMixin` | `shared/datasources/query_mixins.dart:34` | |
| `PagedListProvider` | `shared/providers/paged_list_provider.dart:5` | |
| `AppTime` | `shared/time_provider.dart:74` | |
| `FixedTimeProvider` | `shared/time_provider.dart:52` | |
| `StringUtils` (extension) | `shared/utils/string_utils.dart:19` | |
| `PageNumberSelector` | `shared/widgets/pagination_controls.dart:394` | |
| `PaginationBar` | `shared/widgets/pagination_controls.dart:183` | |
| `PaginationDots` | `shared/widgets/pagination_controls.dart:315` | |

---

## Part 1: God Classes (Screens & Services)

### 1.1 God Class Inventory

| # | File | Lines | Feature | Core Problem |
|---|------|-------|---------|-------------|
| G1 | `entries/.../report_screen.dart` | **2,761** | Entries | Inline editing for every section, PDF gen, photos, forms, contractors |
| G2 | `entries/.../entry_wizard_screen.dart` | **2,610** | Entries | 40+ fields, form+photo+weather+personnel+equipment+quantities+auto-save |
| G3 | `entries/.../home_screen.dart` | **2,382** | Entries | Calendar nav, split-view preview, inline editing, contractor editing, animations |
| G4 | `pdf/.../column_detector_v2.dart` | **1,948** | PDF | 5 detection layers + orchestrator in single class |
| G5 | `toolbox/.../form_fill_screen.dart` | **1,859** | Toolbox | Form render + auto-fill + quick entry + PDF export + table rows + calculations |
| G6 | `core/theme/app_theme.dart` | **1,568** | Core | 152 lines re-export waste + 3 full Material themes (structurally justified) |
| G7 | `pdf/.../post_processor_v2.dart` | **1,509** | PDF | 6 processing phases in single class, 391-line orchestrator method |
| G8 | `pdf/.../extraction_pipeline.dart` | **1,246** | PDF | 560-line `_runExtractionStages` god method |
| G9 | `services/sync_service.dart` | **1,053** | Sync | 18 identical pull + 14 identical push methods |
| G10 | `pdf/.../row_classifier_v2.dart` | **951** | PDF | **ENTIRELY DEAD CODE** -- V3 replaced it |

---

### 1.2 Entries Feature -- Refactoring Opportunities (18 items)

The entries feature is the worst offender: 8,466 lines across 4 screens with massive duplication between them.

#### P0 -- Critical

| ID | What | Files | Lines Saveable | Effort | Dependencies |
|----|------|-------|---------------|--------|-------------|
| E-01 | **Extract EntryEditingController** -- 7 identical TextEditingControllers + 7 FocusNodes + save/populate/dispose duplicated across 3 screens | report_screen, home_screen, entry_wizard_screen | ~250 | Medium | None |
| E-02 | **Extract ContractorEditingController** -- 12 shared state fields, 90-line save method, legacy personnel mapping all duplicated 3x | report_screen, home_screen, entry_wizard_screen | ~500 | High | E-01 |
| E-03 | **Extract PhotoAttachmentManager** -- capture, pick, save, rename, delete methods duplicated verbatim between 2 screens | report_screen, entry_wizard_screen | ~200 | Medium | None |

#### P1 -- High

| ID | What | Files | Lines Saveable | Effort | Dependencies |
|----|------|-------|---------------|--------|-------------|
| E-04 | Extract FormAttachmentManager (select, start, open, delete) | report_screen, entry_wizard_screen | ~100 | Low | None |
| E-05 | Decompose ReportScreen into section widgets | report_screen (2,761 lines) | ~400 | High | E-01, E-02 |
| E-06 | Decompose `_generateReport()` god method (254 lines) + `_saveAsDraft()` (91 lines) -- 4 copies of DailyEntry field construction in one file | entry_wizard_screen | ~200 | Medium | E-01 |
| E-07 | Decompose HomeScreen (move inner widgets, extract shared contractor section) | home_screen (2,382 lines) | ~300 | High | E-01, E-02 |
| E-08 | Fix DI violations -- `DatabaseService()` directly instantiated in 3 screens | all 3 screens | ~30 | Low | None |
| E-09 | Remove legacy personnel fallback code -- dual-track counting (dynamic + hardcoded foreman/operator/laborer) with string matching | all 3 screens (~450 lines total) | ~350 | Medium | E-02, DB migration |
| E-14 | Replace stringly-typed contractor data (`Map<String, dynamic>` with 40+ accesses) | entry_wizard_screen | ~0 (type safety) | Medium | None |

#### P2 -- Medium

| ID | What | Files | Lines Saveable | Effort | Dependencies |
|----|------|-------|---------------|--------|-------------|
| E-10 | Extract ContextualFeedbackOverlay (identical animated overlay in 2 files) | home_screen, entries_list_screen | ~75 | Low | None |
| E-11 | Extract DeleteEntryDialog (identical 80-line dialog in 2 files) | home_screen, entries_list_screen | ~80 | Low | None |
| E-12 | Extract StatusBadge widget (status color/text/icon switch duplicated 4x) | report_screen, home_screen, entries_list_screen | ~80 | Low | None |
| E-15 | Extract data loading orchestration (~100-line method duplicated 3x) | all 3 screens | ~200 | Medium | E-08 |
| E-16 | DI for PdfService (directly instantiated) | report_screen | ~1 | Trivial | None |
| E-17 | Extract PdfDataBuilder from `_exportPdf()` god method (142 lines) | report_screen | ~50 | Medium | E-16 |
| E-18 | DI for WeatherService and ImageService | entry_wizard_screen | ~2 | Trivial | None |

#### P3 -- Low

| ID | What | Files | Lines Saveable | Effort | Dependencies |
|----|------|-------|---------------|--------|-------------|
| E-13 | Extract shared `_buildSimpleInfoRow` widget | report_screen, home_screen | ~22 | Trivial | None |

**Entries total estimated savings: ~2,840 lines (33% of current 8,466)**

---

### 1.3 PDF Extraction Pipeline -- Refactoring Opportunities (14 items)

#### P0 -- Critical

| ID | What | File | Lines Saveable | Effort | Dependencies |
|----|------|------|---------------|--------|-------------|
| P-01 | **Delete RowClassifierV2** -- entire file is dead code, V3 is active, not in barrel export | row_classifier_v2.dart | **~951** | Small | Retarget/delete 2 test files |
| P-02 | **Fix firstWhere crash** at post_processor_v2.dart:369 -- item number rewriting makes the lookup fail | post_processor_v2.dart | 0 (bug fix) | Trivial | None |

#### P1 -- High

| ID | What | File | Lines Saveable | Effort | Dependencies |
|----|------|------|---------------|--------|-------------|
| P-03 | **Decompose ColumnDetectorV2** into HeaderDetector, TextAlignmentDetector, WhitespaceGapDetector, AnchorCorrector + orchestrator (self-aware TODO already exists at lines 11-16) | column_detector_v2.dart (1,948 lines) | 0 (redistribution) | Large | None |
| P-04 | **Decompose PostProcessorV2** into ValueNormalizer, RowSplitter, ConsistencyChecker, ItemDeduplicator (self-aware TODO at lines 20-25) | post_processor_v2.dart (1,509 lines) | 0 (redistribution) | Large | None |
| P-06 | Extract duplicate column ratio constants (`_provisionalColumnRatios` = `_fallbackRatios`) | extraction_pipeline.dart + column_detector_v2.dart | ~8 | Trivial | None |

#### P2 -- Medium

| ID | What | File | Lines Saveable | Effort | Dependencies |
|----|------|------|---------------|--------|-------------|
| P-05 | Extract `_runExtractionStages` sub-algorithms (560-line god method, especially 200-line synthetic region merge) | extraction_pipeline.dart | 0 (redistribution) | Medium | None |
| P-07 | Extract shared row grouping utilities from V3 (after V2 deletion) | row_classifier_v3.dart | ~100 | Small | P-01 |
| P-08 | Move `columnsForPage()` to ColumnMap model (duplicated in V3 + cell_extractor) | row_classifier_v3.dart, cell_extractor_v2.dart | ~10 | Trivial | None |

#### P3 -- Low

| ID | What | File | Lines Saveable | Effort | Dependencies |
|----|------|------|---------------|--------|-------------|
| P-09 | Extract shared keyword matching (3 implementations) | column_detector_v2, row_classifier_v2, row_classifier_v3 | ~20 | Small | None |
| P-10 | Address isolate `_median` duplication (4th copy, constraint is real) | grid_line_detector.dart | ~12 | Small | None |
| P-11 | Extract `_CropOcrStats` to own file (190 lines of stats boilerplate) | text_recognizer_v2.dart | ~190 (move) | Small | None |
| P-12 | Data-drive encoding corruption rules in `cleanDescriptionArtifacts` (126-line method with 14+ regexes) | post_process_utils.dart | 0 (restructure) | Medium | None |
| P-13 | Extract shared OcrTextExtractor for M&P (simplified pipeline duplicate) | mp_extraction_service.dart | ~30 | Medium | None |

**PDF total: ~951 lines deletable + ~1,170 lines redistributable for testability**

---

### 1.4 Toolbox Feature -- Refactoring Opportunities

#### CRITICAL: Feature Split Required

The toolbox feature contains **76 files** with **7 independent sub-features** crammed into one directory. This violates feature-first architecture.

| # | Sub-Feature | Files | Est. Lines | Recommendation |
|---|------------|-------|-----------|---------------|
| 1 | Forms (templates, fill, import, mapping, field registry) | ~45 | ~8,500 | `lib/features/forms/` |
| 2 | Calculator (HMA, Concrete, history) | ~5 | ~1,300 | `lib/features/calculator/` |
| 3 | Gallery (photo viewer, filters) | ~2 | ~850 | Merge into `lib/features/photos/` or own feature |
| 4 | Todos (task management) | ~4 | ~1,100 | `lib/features/todos/` |
| 5 | PDF Export (template filling, preview) | ~3 | ~1,100 | Stays with forms |
| 6 | Auto-Fill (engine, context builder) | ~6 | ~1,800 | Stays with forms |
| 7 | Toolbox Home (launcher grid) | 1 | 124 | Stays as `lib/features/toolbox/` shell |

**Calculator and Todos have ZERO cross-dependencies** -- they can be extracted with only import path changes.

#### God Class: FormFillScreen (1,859 lines, 16 state variables)

| ID | What | Lines Saveable | Effort |
|----|------|---------------|--------|
| T-01 | Extract auto-fill state to `FormAutoFillController` | Part of ~400 redistribution | Medium |
| T-02 | Extract parsing state to `FormParsingController` | Part of ~400 redistribution | Medium |
| T-03 | Extract calculation state to provider | Part of ~400 redistribution | Low |
| T-04 | Extract project prefill logic to service | ~62 | Low |
| T-05 | Fix DI violation -- manual `FieldRegistryService` + `AutoFillEngine` construction | ~3 | Trivial |

#### Service Layer

| ID | What | File | Lines Saveable | Effort |
|----|------|------|---------------|--------|
| T-06 | **Delete hardcoded form definitions** -- JSON assets exist, fallback is dead code | form_seed_service.dart | **~440** | Low |
| T-07 | Extract TemplateLoader, PdfFieldFiller, PreviewCache from service | form_pdf_service.dart (939 lines) | 0 (redistribution) | Medium |
| T-08 | Extract TemplateValidationService from field_registry_service | field_registry_service.dart (596 lines) | 0 (redistribution) | Medium |

#### Widget Extractions (private widgets already defined, just need own files)

| Source | Widget | Lines |
|--------|--------|-------|
| todos_screen.dart | `_TodoCard`, `_DueDateChip`, `_TodoDialog` | 380 |
| calculator_screen.dart | `_HmaCalculator`, `_ConcreteCalculator` + shared result card + history section | 630 |
| gallery_screen.dart | `_FilterSheet`, `_PhotoViewerScreen` | 281 |
| field_mapping_screen.dart | `_StatChip`, `_FieldMappingCard`, `_ConfidenceChip` | 197 |
| form_fill_screen.dart | Export dialog, project prefill dialog, remap warning banner | 166 |

#### DRY Violations

| What | Locations | Lines Saved |
|------|-----------|------------|
| Calculator result card (identical 2x) | calculator_screen.dart | 59 |
| Calculator history section (identical 2x) | calculator_screen.dart | 26 |
| `_parsePdfFieldType` switch (identical 2x) | field_registry_service + form_fill_screen | 18 |
| `_parseAutoFillSource` switch (identical 2x) | field_registry_service + form_fill_screen | 24 |
| Hardcoded form definitions (dead) | form_seed_service.dart | 440 |

**Toolbox total: ~440 lines deletable + ~780 DRY savings + major structural split**

---

## Part 2: Cross-Cutting Architecture Debt

### 2.1 main.dart -- Service Locator Anti-Pattern (624 lines)

| Metric | Count |
|--------|-------|
| Import statements | 82 |
| Datasource instantiations | 16 |
| Repository instantiations | 13 |
| Service instantiations | 8 |
| Constructor parameters | 26 |
| Provider registrations | 28 |

Every new feature requires touching this file in 4-6 places. Two datasources bypass the repository pattern entirely (calculator history, todo items).

**Fix**: Feature-module registration pattern where each feature exposes `registerProviders()`. Estimated savings: ~400 lines.

### 2.2 SyncService Duplication (1,053 lines, ~550 saveable)

- 18 identical `_pullX()` methods (3 lines each, same body)
- 14 identical push blocks in `_pushBaseData()` (~10 lines each)
- Dual `SyncResult` classes (legacy + new domain)
- 3 unused remote datasource fields with `// ignore: unused_field`
- Stalled migration: `SyncOrchestrator` built but never wired in

**Fix**: Table-config-driven loops. Already has a `tables` list defined.

### 2.3 Repository save() Duplication (11 identical implementations)

Same check-existing-then-insert-or-update in every repository. Plus `getById()`, `getAll()`, `delete()` are simple pass-throughs in 10 of 11.

**Fix**: `BaseCrudRepository<T>` with default implementations. Savings: ~175 lines.

### 2.4 Provider Inconsistency (5 use BaseListProvider, 15 use raw ChangeNotifier)

Of the 15 raw ChangeNotifier providers, at least 4 (`PhotoProvider`, `InspectorFormProvider`, `TodoProvider`, `EquipmentProvider`) duplicate the exact loading/error/CRUD boilerplate that `BaseListProvider` provides. Additionally, 3 providers duplicate identical ~55-line pagination logic.

**Fix**: Adopt `BaseListProvider` where applicable + create `PaginationMixin`. Savings: ~150 lines.

### 2.5 Dead Code at Project Level

| Item | File | Lines | Status |
|------|------|-------|--------|
| `SecureStorageService` | `lib/services/secure_storage_service.dart` | 182 | Zero imports anywhere -- delete |
| `SyncOrchestrator` + adapters | `lib/features/sync/application/` | ~350 | Built but never wired in |
| 3 unused SyncService fields | `lib/services/sync_service.dart:131-136` | 6 | `// ignore: unused_field` |
| `RowClassifierV2` | `pdf/.../row_classifier_v2.dart` | 951 | V3 replaced, not in barrel |
| 3 orphaned V1 stage files | `pdf/.../stages/{document_analyzer,native_extractor,structure_preserver}.dart` | ~300 est. | Duplicate `deprecated/` |
| Hardcoded form definitions | `toolbox/.../form_seed_service.dart:296-735` | 440 | JSON assets exist |
| Theme re-export bridge | `core/theme/app_theme.dart:1-152` | 152 | Pure backward-compat indirection |
| Seed data inline | `core/database/seed_data_service.dart` | ~450 | Should be JSON assets |

### 2.6 DI Violations (Direct Service Instantiation in Screens)

| File | Service Created Directly |
|------|------------------------|
| `report_screen.dart:113` | `DatabaseService()` -> datasources |
| `home_screen.dart:104` | `DatabaseService()` -> datasources |
| `entry_wizard_screen.dart:123` | `DatabaseService()` -> datasources |
| `entry_wizard_screen.dart:104-105` | `WeatherService()`, `ImageService()` |
| `report_screen.dart:54` | `PdfService()` |
| `form_fill_screen.dart:156-158` | `FieldRegistryService()` |
| `form_fill_screen.dart:332` | `AutoFillEngine()` |

---

## Part 3: Crash Risks & Bug Fixes

| # | Severity | File:Line | Issue | Fix |
|---|----------|-----------|-------|-----|
| B-01 | **CRITICAL** | `post_processor_v2.dart:369` | `.firstWhere()` without `orElse` -- item number rewriting makes lookup fail | `.where(...).firstOrNull` |
| B-02 | Medium | `column_detector_v2.dart:1055` | `.firstWhere()` with try-catch anti-pattern | `.firstOrNull` |
| B-03 | Medium | 11 locations in PDF models | `.firstWhere()` in enum `fromMap` factories | Acceptable (fail-fast on corrupt data) |
| B-04 | Medium | `equipment_provider.dart:119-127` | N+1 query -- one DB query per contractor in loop | Batch `WHERE IN` query |
| B-05 | Low | `image_service.dart:130-156` | `_generateThumbnailIsolate` returns original bytes unchanged | Implement resize or rename |

---

## Part 4: Test Debt

| Issue | Files | Impact |
|-------|-------|--------|
| 5 test files validate deprecated code, not production | `stage_0_document_analyzer_test`, `document_analyzer_integration_test`, `stage_2a_native_extractor_test`, `stage_3_structure_preserver_test`, `stage_0_to_2_contract_test` | False confidence -- tests pass but don't test running code |
| 2 test files reference dead RowClassifierV2 | `stage_4a_row_classifier_test`, `stage_4a_to_4b_contract_test` | Testing dead code |
| Duplicate golden fixture test | `integration_test/` + `test/` both have generate_golden_fixtures_test.dart | Confusion about which to run |
| 485 `debugPrint` calls across 48 files | Entire codebase | Should use `AppLogger`/`DebugLogger` |

---

## Part 5: Feature Architecture Consistency

| Feature | data/ | presentation/ | domain/ | Consistent? | Notes |
|---------|:-----:|:-------------:|:-------:|:-----------:|-------|
| contractors | Y | Y | -- | Standard | |
| locations | Y | Y | -- | Standard | |
| projects | Y | Y | -- | Standard | |
| photos | Y | Y | -- | Standard | |
| quantities | Y | Y | -- | Standard | |
| entries | Y | Y (+models) | -- | Non-standard | Has `presentation/models/` |
| toolbox | Y | Y | -- | **CRITICAL** | 76 files, 7 sub-features -- needs split |
| sync | Y | Y | Y | Full Clean Arch | Only feature with domain layer |
| auth | -- | Y | -- | Incomplete | Missing data layer |
| settings | -- | Y | -- | Incomplete | Missing data layer |
| dashboard | -- | Y | -- | Minimal | Screen-only |
| pdf | models | Y | -- | Non-standard | Core logic in `services/`, 3 arch layers |
| weather | -- | -- | -- | Service-only | No feature structure |

---

## Part 6: Positive Observations

These patterns are **working well** and should be preserved/extended:

- **GenericLocalDatasource** + **ProjectScopedDatasource** -- excellent base abstractions
- **BaseListProvider** -- eliminates ~100 lines of boilerplate per adopting provider
- **RepositoryResult<T>** -- clean error handling without exceptions
- **Data-accounting assertions** in PDF pipeline -- `inputCount + excludedCount == outputCount`
- **Normalized coordinates (0.0-1.0)** throughout extraction pipeline
- **Dependency injection in ExtractionPipeline** -- 18 stages, all optional with defaults
- **Safe DB migrations** with `_addColumnIfNotExists` pattern
- **Stage isolation** -- typed I/O with no hidden mutable state between stages
- **Barrel exports** -- consistent and well-maintained
- **`mounted` checks** -- consistently applied after async operations across all screens
- **Widget extraction started** -- `report_widgets/`, `ContractorEditorWidget`, `EntryBasicsSection` show the pattern
- **Testing keys** -- extensive `TestingKeys.*` usage enables Flutter Driver automation
- **Auto-fill context builder** -- graceful null handling with degradation

---

## Master Priority Matrix

### Tier 1: Quick Wins (Low effort, high impact, no dependencies)

| ID | What | Effort | Lines Saved |
|----|------|--------|------------|
| P-02 | Fix firstWhere crash in post_processor_v2 | Trivial | 0 (bug fix) |
| P-01 | Delete RowClassifierV2 (dead file) | Small | ~951 |
| T-06 | Delete hardcoded form definitions | Low | ~440 |
| A-03 | Delete secure_storage_service.dart | Trivial | 182 |
| E-08 | Fix DI violations (DatabaseService in 3 screens) | Low | ~30 |
| E-11 | Extract DeleteEntryDialog | Low | ~80 |
| E-12 | Extract StatusBadge widget | Low | ~80 |
| P-06 | Extract duplicate column ratio constants | Trivial | ~8 |
| -- | Delete 3 orphaned V1 stage files | Trivial | ~300 est. |

**Tier 1 total: ~2,070 lines, 1-2 days effort**

### Tier 2: Core Extractions (Medium effort, highest modularity impact)

| ID | What | Effort | Lines Saved |
|----|------|--------|------------|
| E-01 | Extract EntryEditingController | Medium | ~250 |
| E-03 | Extract PhotoAttachmentManager | Medium | ~200 |
| E-04 | Extract FormAttachmentManager | Low | ~100 |
| E-14 | Type-safe contractor edit state | Medium | 0 (safety) |
| E-02 | Extract ContractorEditingController | High | ~500 |
| A-04 | Repository BaseCrudRepository with default save() | Medium | ~175 |
| A-02 | SyncService table-driven dedup | Medium | ~550 |

**Tier 2 total: ~1,775 lines, 3-5 days effort**

### Tier 3: Structural Decomposition (High effort, long-term maintainability)

| ID | What | Effort | Lines Saved |
|----|------|--------|------------|
| E-05 | Decompose ReportScreen sections | High | ~400 |
| E-06 | Decompose _generateReport god method | Medium | ~200 |
| E-07 | Decompose HomeScreen | High | ~300 |
| P-03 | Decompose ColumnDetectorV2 | Large | 0 (redistribution) |
| P-04 | Decompose PostProcessorV2 | Large | 0 (redistribution) |
| A-01 | main.dart feature-module registration | Medium | ~400 |
| T-split | Split toolbox into calculator, todos, gallery, forms | Medium | 0 (restructure) |

**Tier 3 total: ~1,300 lines + major restructuring, 5-8 days effort**

### Tier 4: Legacy Cleanup & Migration

| ID | What | Effort | Lines Saved |
|----|------|--------|------------|
| E-09 | Remove legacy personnel fallback code | Medium | ~350 |
| A-sync | Complete sync architecture migration | High | ~800 net |
| A-prov | Standardize providers to BaseListProvider | Medium | ~150 |
| T-tests | Rewrite 7 test files testing deprecated code | Medium | 0 (correctness) |
| T-debug | Migrate 485 debugPrint calls to AppLogger | Medium | 0 (quality) |
| T-seed | Extract seed data to JSON assets | Low | ~450 |

**Tier 4 total: ~1,750 lines + correctness improvements, 4-6 days effort**

---

## Recommended Execution Order

1. **Tier 1 quick wins** -- Immediate value, builds momentum, no risk
2. **Toolbox split** (calculator + todos) -- Zero-dependency extraction, reduces feature sprawl immediately
3. **Entry controllers** (E-01, E-02, E-03) -- Unblocks all screen decomposition
4. **Screen decomposition** (E-05, E-06, E-07) -- Biggest god classes broken up
5. **Architecture patterns** (BaseCrudRepository, main.dart modularization) -- Scales future development
6. **PDF pipeline decomposition** (P-03, P-04) -- Improves testability of extraction
7. **Sync migration** -- Complete the stalled Clean Architecture migration
8. **Legacy cleanup** -- Personnel code removal, provider standardization, test rewrites

---

## How to Re-run Analysis

```bash
# Full prunekit scan
pwsh -Command "dart run flutter_prunekit unused_code"

# Types only (highest confidence)
pwsh -Command "dart run flutter_prunekit unused_code --only-types"

# JSON output for tooling
pwsh -Command "dart run flutter_prunekit unused_code --json"

# Flutter static analysis
pwsh -Command "flutter analyze"

# File size audit (find god classes)
find lib -name "*.dart" -exec wc -l {} + | sort -rn | head -30
```
