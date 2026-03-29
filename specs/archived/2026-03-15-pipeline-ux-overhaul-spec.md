# Spec: PDF Pipeline UX Overhaul — Background Processing, Progress, Logger

**Date**: 2026-03-15
**Status**: FINAL — post-adversarial review
**Delivery**: 2 PRs — PR1 (architecture), PR2 (logger migration)

## Context

PDF extraction on S25 Ultra takes 265 seconds (4.5 min) for a 6-page Springfield PDF. OCR alone is 242 seconds (91%). The entire pipeline runs on the main UI thread — Android shows an ANR dialog. Progress UI shows "Page X of 15" (hardcoded stage count), freezes with no updates, and has unmapped stages. The Logger system has massive coverage gaps. A Tesseract re-init bug forces tessdata reload on every OCR call.

### Strategy: Fix First, Measure, Then Decide

The re-init bug likely accounts for 200+ of the 242 seconds (hundreds of crops × 0.5-1s per unnecessary `Init()`). We will:
1. Fix the re-init bug
2. Move pipeline to a single background isolate (no sub-isolates)
3. Measure OCR time on device
4. Only add parallel workers later if still needed

This eliminates the riskiest items (unproven isolate-in-isolate FFI, 4-worker complexity) while still hitting the performance target.

### Success Criteria
1. Zero ANR dialogs during extraction
2. User can navigate within the app while extraction runs (bottom banner)
3. Warning shown that extraction fails if user leaves the app
4. Progress shows accurate page/cell counts with smooth updates
5. OCR time reduced significantly (target: under 1.5 min via re-init fix alone)
6. All pipeline stages emit structured Logger calls
7. Full app-wide migration from deprecated DebugLogger + debugPrint → Logger
8. Release-safe logging (no auth data, PII, or device identifiers in file transport)
9. After project save, user lands on dashboard

---

## PR1: Architecture — Background Isolate + Progress UX + Project Save

### 1. Tesseract Re-init Fix

**Problem**: `packages/flusseract/lib/tesseract.dart:68-71` — `setPageSegMode()` unconditionally sets `_needsInit = true`, forcing full `TessBaseAPI::Init()` (14.7MB LSTM reload) on every OCR call.

**Fix**: Guard both `setPageSegMode()` and `setWhiteList()` to skip when value unchanged:
```dart
void setPageSegMode(PageSegMode mode) {
  if (_pageSegMode == mode) return;
  _pageSegMode = mode;
  _needsInit = true;
}
```
Also guard in `TesseractEngineV2.recognizeImage()` — skip `tess.setPageSegMode()` and `tess.setWhiteList()` calls when config matches previous call.

**Files**:
- `packages/flusseract/lib/tesseract.dart`
- `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`

### 2. Single Background Isolate

**Architecture**: One worker isolate, one Tesseract instance, sequential page processing.

```
Main Isolate                     Worker Isolate
┌───────────────┐               ┌────────────────────┐
│ ImportHelper   │──submit job─▶│ ExtractionJobRunner │
│ (bid/M&P)     │              │                     │
│               │◀──progress───│ Pipeline + Tesseract│
│ Banner UI     │◀──stream     │ + OpenCV            │
│               │◀──result─────│                     │
└───────────────┘               └────────────────────┘
```

**Key design:**
- One job at a time
- Worker isolate owns all FFI (Tesseract + OpenCV) — no thread-locality issues
- `SendPort`/`ReceivePort` for progress stream + result delivery
- Tessdata path resolved on main isolate, passed to worker as parameter (avoids platform channel `MissingPluginException` in isolates)
- PDF bytes sent via `TransferableTypedData` (zero-copy)
- Worker spawned lazily, killed on `dispose()`
- Cancel only takes effect between pages (can't interrupt FFI mid-call)
- Memory pressure handler: kill worker if no job in progress, re-spawn lazily
- Result stored in `ExtractionJobRunner` provider state (not just route `extra`) for reliable delivery

**Job model:**
```dart
sealed class ExtractionJob {
  final Uint8List pdfBytes;
  final String projectId;
}
class BidItemExtractionJob extends ExtractionJob { ... }
class MpExtractionJob extends ExtractionJob {
  final List<Map<String, dynamic>> existingBidItemMaps; // serialized for isolate boundary
}
```

**Size limit**: Reject PDFs over 100MB before spawning isolate.

**Background warning**: Show a dialog when extraction starts: "Please keep the app open during extraction. Switching to another app may cancel the process."

**New files:**
- `lib/features/pdf/services/extraction/runner/extraction_job_runner.dart`
- `lib/features/pdf/services/extraction/runner/extraction_job.dart`
- `lib/features/pdf/services/extraction/runner/extraction_result.dart`

**Modified files:**
- `lib/features/pdf/presentation/helpers/pdf_import_helper.dart` — submit job
- `lib/features/pdf/presentation/helpers/mp_import_helper.dart` — submit job + fix: call `dispose()` on `MpExtractionService`
- `lib/main.dart` — register `ExtractionJobRunner` as provider

### 3. Progress Reporting

**Progress model:**
```dart
class ExtractionProgress {
  final String stageName;
  final String stageLabel;      // user-friendly
  final int stageIndex;
  final int totalStages;        // dynamic, not hardcoded 15
  final int? pageIndex;
  final int? totalPages;
  final double overallPercent;
  final Duration elapsed;
}
```

**Per-stage granular callbacks** — add `onProgress` to:
- `PageRendererV2.render()` — per-page
- `ImagePreprocessorV2.preprocess()` — per-page
- `GridLineDetector.detect()` — per-page
- `GridLineRemover.remove()` — per-page
- `TextRecognizerV2.recognize()` — per-page AND per-cell

**Fix unmapped stage**: Add `analyzingDocument` to `ExtractionStage` enum.

**Remove hardcoded `totalStages=15`**: Replace with dynamic count based on actual pipeline path.

**Stage labels:**

| Internal | User Label |
|----------|------------|
| analyzingDocument | Analyzing document... |
| rendering | Rendering pages... |
| preprocessing | Preprocessing images... |
| gridDetection | Detecting table structure... |
| gridRemoval | Cleaning table borders... |
| ocr | Reading cell contents... |
| validation | Validating extracted data... |
| parsing | Building bid items... |
| postProcessing | Verifying accuracy... |
| complete | Import complete! |

**Modified files:**
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- `lib/features/pdf/services/extraction/stages/page_renderer_v2.dart`
- `lib/features/pdf/services/extraction/stages/image_preprocessor_v2.dart`
- `lib/features/pdf/services/extraction/stages/grid_line_detector.dart`
- `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`

### 4. UI — Bottom Banner

**ExtractionBanner** — root-level overlay (NOT inside ShellRoute — must be visible on full-screen routes too):
- Slim strip (~48dp) above bottom nav bar
- Shows: stage icon + stage label + progress bar + elapsed time
- Tappable → bottom sheet with full stage breakdown + cancel button
- Cancel labeled: "Cancel (takes effect after current page)"
- On completion: turns green "Import complete! Tap to review" → navigates to preview screen
- Auto-dismiss after 10 seconds if user doesn't tap

**New files:**
- `lib/features/pdf/presentation/widgets/extraction_banner.dart`
- `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart`

**Modified files:**
- `lib/core/router/app_router.dart` — add root-level overlay
- `lib/features/pdf/presentation/widgets/pdf_import_progress_dialog.dart` — deprecate
- `lib/features/pdf/presentation/widgets/pdf_import_progress_manager.dart` — deprecate

### 5. Project Save Flow Fix

After `_saveProject()` succeeds for a new project:
1. `projectProvider.selectProject(_projectId!)`
2. `context.goNamed('dashboard')`

Matches existing pattern at `project_list_screen.dart:511-514`.

**File**: `lib/features/projects/presentation/screens/project_setup_screen.dart` (line ~863)

### 6. Security Fixes (in PR1 scope)

- **Firebase API key**: Restrict in GCP console (Android app + API restriction). Verify gitignored.
- **`systemTemp` fallback**: Replace with `getTemporaryDirectory()` in `logger.dart:639-658`
- **PDF size limit**: Reject >100MB before isolate spawn
- **`allowBackup="false"`**: Add to `AndroidManifest.xml` `<application>` element
- **Move `QUERY_ALL_PACKAGES` + `MANAGE_EXTERNAL_STORAGE`** to `src/debug/AndroidManifest.xml`

---

## PR2: App-Wide Logger Migration

### 7A: Release-Safe File Logging

Add a release filter to the file transport. In release builds:
- **Log**: PDF pipeline, sync errors, DB operations, navigation, UI errors, weather
- **Scrub**: Auth operations (strip to operation name only, no user context), device identifiers, PII
- **Never log in release**: tokens, passwords, emails, phone numbers, inspector names, company names, addresses, GPS coordinates

Add construction-domain fields to PII scrub blocklist:
```
'filename', 'project_name', 'contractor_name', 'location_name', 'site_address'
```
Plus `_endsWith` variants for `_address`, `_location`.

Fix HTTP transport scrub ordering: run `_scrubSensitive()` before truncation check.

Add log retention: delete session folders older than 14 days on startup. Cap at 50MB total.

**File**: `lib/core/logging/logger.dart`

### 7B: Migrate 22 DebugLogger Files → Logger

Mechanical replacement. Full list:

**PDF (5):** `extraction_pipeline.dart`, `post_processor_v2.dart`, `pdf_import_service.dart`, `pdf_import_helper.dart`, `grid_line_remover.dart`

**Sync (6):** `sync_engine.dart`, `sync_orchestrator.dart`, `sync_lifecycle_manager.dart`, `change_tracker.dart`, `orphan_scanner.dart`, `integrity_checker.dart`

**Database (2):** `database_service.dart`, `schema_verifier.dart`

**Services (3):** `soft_delete_service.dart`, `startup_cleanup_service.dart`, `storage_cleanup.dart`

**Projects (2):** `project_repository.dart`, `project_local_datasource.dart`

**Quantities (2):** `bid_item_provider.dart`, `budget_sanity_checker.dart`

**Shared (1):** `generic_local_datasource.dart`

### 7C: Migrate 49 debugPrint Files → Logger

Replace `debugPrint()` with appropriate `Logger` category calls. Category mapping per file documented in spec Section 7B of the original draft (preserved for reference).

### 7D: Add Logging to 16 Dark Pipeline Stages

**Critical:** `DocumentQualityProfiler`, `RowClassifierV3`, `RowParserV3`, `FieldConfidenceScorer`, `ItemDeduplicator`

**Important:** `CellExtractorV2`, `ColumnDetectorV2`, `RegionDetectorV2`, `NumericInterpreter`, `ElementValidator`

**Remaining:** `HeaderDetector`, `RowMerger`, `ValueNormalizer`, `AnchorCorrector`, `ConsistencyChecker`, `OcrEngineV2`, `OcrTextExtractor`

Per-page OCR timing + memory snapshots at key extraction points.

### 7E: Delete Deprecated Wrappers

- Delete `lib/core/logging/debug_logger.dart`
- Delete `lib/core/logging/app_logger.dart`
- Remove all imports app-wide

---

## Verification

### PR1 — On-device test
1. `pwsh -File tools/build.ps1 -Platform android`
2. `adb -s R5CY12JTTPX install -r build/app/outputs/flutter-apk/app-release.apk`
3. Springfield PDF extraction:
   - No ANR dialog
   - Banner shows accurate page counts
   - User can navigate within app during extraction
   - Background warning shown at start
   - **Measure OCR time** — if under 1.5 min with re-init fix alone, parallel workers are not needed
   - 131/131 items, $0 checksum (accuracy unchanged)
4. M&P import — same banner behavior
5. Project creation → save → lands on dashboard
6. Cancel mid-extraction → clean cancellation at page boundary

### PR1 — Unit tests
- `pwsh -Command "flutter test test/features/pdf/"` — existing tests pass
- New tests for `ExtractionProgress` model
- New tests for `ExtractionJobRunner` lifecycle

### PR2 — Logger migration
- `pwsh -Command "flutter test"` — all tests pass
- Verify zero `DebugLogger` or `AppLogger` imports remain: `Grep "DebugLogger\|AppLogger" lib/`
- Check release log files don't contain auth/PII data
- Verify log retention cleanup works

---

## Adversarial Review Summary

Reviews saved to `.claude/adversarial_reviews/2026-03-15-pipeline-ux-overhaul/`.

### Code Review — 7 MUST-FIX (all addressed above)
1. ~~Re-init fix misses whitelist path~~ → Guard both PSM + whitelist
2. ~~Isolate-in-isolate FFI unproven~~ → Single worker, no sub-isolates
3. ~~Result delivery on app kill~~ → Store in provider state + accept limitation
4. ~~Android kills backgrounded app~~ → Warning dialog, accept limitation
5. ~~Uint8List copy cost~~ → TransferableTypedData
6. ~~Platform channel fails in isolates~~ → Pass tessdata path as parameter
7. ~~Cancel mid-FFI impossible~~ → Cancel between pages only

### Security Review — 3 MUST-FIX (all addressed above)
1. ~~Firebase API key unrestricted~~ → Restrict in GCP console
2. ~~File logging ON in release~~ → Release-safe filter (scrub auth/PII)
3. ~~systemTemp fallback world-readable~~ → Use getTemporaryDirectory()

### Deferred to backlog
- Release signing key (SC-4) — tracked separately
- Parallel OCR workers — measure first, add if needed
