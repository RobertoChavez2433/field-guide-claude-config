# Dead Code Analysis Report - flutter_prunekit

**Date**: 2026-02-16
**Tool**: flutter_prunekit v2.4.0 (AST-based static analysis)
**Status**: NEEDS FURTHER VERIFICATION (unused types and unused fields sections unverified)

---

## Scan Summary

| Category | Total | Unused | Usage Rate |
|----------|-------|--------|------------|
| Types (classes, enums, mixins) | 516 | 14 | 97.3% |
| Methods | 2,955 | 577 | 80.5% |
| Variables | 7,916 | 31 | 99.6% |
| Fields | 2,989 | 93 (36 write-only) | 96.9% |

**Analysis time**: ~20 seconds across 432 files.

**Note**: dead_code_analyzer was also tested but hangs infinitely on this project's barrel file chains (Clean Architecture pattern). It was removed from dev dependencies.

---

## Confirmed Dead Code (Verified by Agent Investigation)

### 1. `PostProcessUtils.looksLikeCurrency()`
- **File**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart:328`
- **Verdict**: TRUE DEAD CODE
- Zero callers anywhere. Superseded by `looksLikePriceToken()` which has stricter currency detection.

### 2. `PostProcessUtils.looksLikeQuantity()`
- **File**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart:362`
- **Verdict**: TRUE DEAD CODE
- Zero callers anywhere. Quantity detection now done via `parseQuantity()` and `isValidQuantity()`.

### 3. `HeaderKeywords.matchesColumn()`
- **File**: `lib/features/pdf/services/extraction/shared/header_keywords.dart:53`
- **Verdict**: TRUE DEAD CODE
- Never adopted. Column detection uses `identifyColumn()` and `_matchesKeyword()` instead.

### 4. `SyncResult.total` (getter, legacy class)
- **File**: `lib/services/sync_service.dart:96`
- **Verdict**: TRUE DEAD CODE
- Zero callers on the legacy `SyncResult`.

### 5. `SyncResult.hasErrors` (getter, legacy class)
- **File**: `lib/services/sync_service.dart:95`
- **Verdict**: TRUE DEAD CODE
- The domain-layer `SyncResult` in `sync_adapter.dart` has its own `hasErrors`. This legacy one is never called.

### 6. Entire file: `RowClassifierV2`
- **File**: `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart`
- **Verdict**: TRUE DEAD CODE (production), still referenced by tests
- Not imported anywhere in `lib/`. Not in barrel export `stages.dart`. Pipeline uses `RowClassifierV3`.
- Test file `stage_4a_row_classifier_test.dart` still references it and should be migrated to V3.

### 7. `UnitRegistry.unitAliases` (visibility issue)
- **File**: `lib/features/pdf/services/extraction/shared/unit_registry.dart:8`
- **Verdict**: SHOULD BE PRIVATE
- Only accessed internally. Should be `static const Map<String, String> _unitAliases`.

---

## False Positive Analysis (Methods)

Estimated prunekit accuracy for methods: **~15-20% true positives** (80-100 of 577 are truly dead).

| False Positive Category | Example | Why Not Dead |
|------------------------|---------|--------------|
| Private pipeline methods | `PostProcessorV2._normalizeItem()` | Called internally; prunekit may not track private calls |
| Framework callbacks | `DatabaseService._onCreate()` | Called by SQLite `openDatabase()` via function references |
| Provider/getter patterns | `SyncService.status`, `isOnline` | Accessed via Provider pattern (dynamic dispatch) |
| Barrel-exported symbols | All classes in `stages.dart` | Transitively imported through barrel files |
| Test-only public API | `CropUpscaler.computeScaleFactor()` | Called internally + exercised by tests |

---

## NEEDS FURTHER VERIFICATION

### Unused Types (14 reported, NOT YET VERIFIED)

These types were flagged but need manual verification:

1. `ColumnBoundary` - PDF extraction
2. `TextSpanInfo` - PDF extraction
3. `_GridSearchResult` - PDF extraction
4. `OcrElementExtension` - extension on OCR elements
5. `PdfViewerService` - possibly replaced
6. `_EntryListItem` - private widget class
7. `_ContractorHeader` - private widget class
8. `_PersonnelEntry` - private widget class
9. + 6 others from prunekit output

**Action needed**: Search for each type name across `lib/` and `test/` to confirm no references exist.

### Unused Fields (93 reported, NOT YET VERIFIED)

Notable fields that need verification:

| Class | Field | File | Concern |
|-------|-------|------|---------|
| CropUpscaler | processedWidth, processedHeight | extraction/shared/crop_upscaler.dart:160-161 | Write-only? |
| DebugLogger | _sessionStartTime (static) | core/logging/debug_logger.dart:20 | Never read? |
| DiscoveredField | options | toolbox/data/services/field_discovery_service.dart:24 | Data model field |
| FormCalculationResult | formula | toolbox/data/services/form_calculation_service.dart:30 | Data model field |
| PdfImportResult | metadata, repairNotes, importReportPath, parserUsed | pdf/services/pdf_import_service.dart:33-45 | Future use? |
| SyncAdapter | onStatusChanged, onSyncComplete, onProgressUpdate | sync/domain/sync_adapter.dart:86-93 | Callback fields |
| SyncConfig | maxConcurrentChunks | services/sync_service.dart:65 | Config not consumed |
| SyncService | _formFieldRegistryRemote, _fieldSemanticAliasRemote, _formFieldCacheRemote | services/sync_service.dart:132-136 | Remote datasources |
| _BatchAnalysis | totalItems, hasSufficientShiftSample | pdf extraction post_processor_v2.dart | Internal model |
| _RowFeatures | isFullWidth | extraction/stages/row_classifier_v2.dart:904 | Dead file (V2) |
| _ZoneContext | descriptionColumn | extraction/stages/row_classifier_v3.dart:572 | May be intentional |

**Action needed**: For each field, verify whether it's read anywhere or only written.

---

## Recommended Actions

### Safe to do now (confirmed dead):
1. Remove `looksLikeCurrency()` and `looksLikeQuantity()` from `post_process_utils.dart`
2. Remove `HeaderKeywords.matchesColumn()`
3. Remove `SyncResult.total` and `SyncResult.hasErrors` from legacy `SyncResult` in `sync_service.dart`
4. Delete `row_classifier_v2.dart` and migrate test to V3
5. Make `UnitRegistry.unitAliases` private

### After verification:
6. Clean up confirmed unused types (14 candidates)
7. Clean up confirmed unused fields (93 candidates)
8. Triage remaining ~80-100 truly dead methods from the 577 reported

---

## How to Re-run This Scan

```bash
# Full scan
pwsh -Command "dart run flutter_prunekit unused_code"

# Types only (highest confidence)
pwsh -Command "dart run flutter_prunekit unused_code --only-types"

# Methods only
pwsh -Command "dart run flutter_prunekit unused_code --only-methods"

# Variables/fields only
pwsh -Command "dart run flutter_prunekit unused_code --only-variables"

# JSON output for tooling
pwsh -Command "dart run flutter_prunekit unused_code --json"

# Exclude directories
pwsh -Command "dart run flutter_prunekit unused_code --exclude 'lib/legacy/**'"
```

---

## Tooling Notes

- **flutter_prunekit** (v2.4.0, AST-based): Works well with this codebase. ~20s scan time. Good for types/variables, noisy for methods due to dynamic dispatch.
- **dead_code_analyzer** (regex-based): INCOMPATIBLE with this project's barrel file architecture. Hangs in infinite export resolution loop. Removed from dev dependencies.
- **Warning**: prunekit reported 116 files with dynamic type usage that may cause false negatives (dead code it can't detect because references are resolved at runtime).
