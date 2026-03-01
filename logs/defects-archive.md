# Defects Archive

Historical defects moved from per-feature defect files. Reference only.

---

## Archived from _defects-auth.md (2026-02-28)

### [DATA] 2026-02-22: RLS locks columns that code tries to update
**Pattern**: `update_own_profile` RLS policy locks `last_synced_at` via WITH CHECK subselect. Client-side `.update({'last_synced_at': ...})` silently fails. Required SECURITY DEFINER RPC bypass.
**Prevention**: When RLS locks a column, any client code updating that column needs a SECURITY DEFINER RPC. Audit RLS WITH CHECK clauses against all Dart `.update()` calls.
**Ref**: @supabase/migrations/20260222100000_multi_tenant_foundation.sql, @lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart

### [DATA] 2026-02-22: fromJson/fromMap column name mismatches with Supabase
**Pattern**: Dart model `fromJson()` used `created_at`/`updated_at` but Supabase table has `requested_at`/`resolved_at`. Also `user_id` vs `id` mismatch. Caused null cast crashes at runtime.
**Prevention**: Always cross-reference Supabase table column names with Dart fromJson() factories. Use `?? json['alt_name']` fallback pattern for columns that differ between local/remote schemas.
**Ref**: @lib/features/auth/data/models/company_join_request.dart, @lib/features/auth/data/models/user_profile.dart

### [DATA] 2026-02-22: Enum values must match Supabase CHECK constraints exactly
**Pattern**: Dart `UserRole` enum had `member` but Supabase CHECK enforced `engineer`/`inspector`. RPC calls sent `'member'` which was rejected server-side.
**Prevention**: Enum `.name` values sent to Supabase RPCs must match the CHECK constraint values exactly. Add a `toDbString()` method if Dart enum names differ from DB values.
**Ref**: @lib/features/auth/data/models/user_role.dart

### [FLUTTER] 2026-02-22: Provider canWrite callbacks not wired
**Pattern**: Providers accept `bool Function() canWrite` callback but it defaults to `() => true` and is never connected to `AuthProvider.canWrite` in `main.dart`.
**Prevention**: When adding canWrite guards to providers, also update `main.dart` provider registration to pass `canWrite: () => authProvider.canWrite`.
**Ref**: All 8+ providers with canWrite (contractor, equipment, personnel_type, todo, location, daily_entry, inspector_form, photo)

### [CONFIG] 2026-02-22: Wrong Supabase key type hardcoded
**Pattern**: `sb_publishable_...` (default publishable key) used instead of JWT `anon` key (`eyJhbG...`). Supabase client silently fails auth — no session restored, no profile loaded.
**Prevention**: Supabase anon key is always a ~200-char JWT starting with `eyJ`. The `sb_publishable_*` key is a different key type. Always verify key format.
**Ref**: @lib/core/config/supabase_config.dart

## Archived from _defects-auth.md (2026-02-28)

### [FLUTTER] 2026-02-22: createCompany doesn't refresh local profile state
**Pattern**: RPC `create_company` sets `status=approved, role=admin` server-side, but `AuthProvider.createCompany()` only updates `_company`, not `_userProfile`. Router sees stale `status=pending` and redirects to wrong screen.
**Prevention**: After any Supabase RPC that modifies user_profiles server-side, always call `await loadUserProfile()` to sync local state.

### [FLUTTER] 2026-02-22: Onboarding routes exempt from profile-based redirect
**Pattern**: `_kOnboardingRoutes` were fully exempt from redirect checks. If profile loads async and user is already on `/profile-setup`, go_router re-evaluates but returns `null` for onboarding routes — user stays stuck even when fully approved.
**Prevention**: Onboarding route exemption must still check if user is fully set up (approved + has company) and redirect to `/` if so.

---

## Archived from _defects-auth.md (2026-02-22)

### [DATA] 2026-02-22: Schema column omissions in parallel worktree implementations
**Pattern**: Agent implementing migration missed `entry_personnel_counts` and `entry_personnel` when adding `created_by_user_id` to "all 17 tables" — easy to miss tables near the end of a long list.
**Prevention**: After schema migrations, run a verification query counting columns across ALL target tables. Use a checklist with explicit table names.
**Ref**: @lib/core/database/database_service.dart, @lib/core/database/schema/personnel_tables.dart

---

## Archived from _defects-quantities.md (2026-02-21)

### [RESOLVED] 2026-02-20: DuplicateStrategy switch fallthrough in importBatch
**Status**: FIXED (Session 399).
**Pattern**: `importBatch` duplicate handling switch lacked explicit `break`s, causing fallthrough and incorrect duplicate behavior paths.
**Prevention**: Require explicit `break` in duplicate strategy switch and include strategy-path tests for skip/replace/error.
**Ref**: @lib/features/quantities/presentation/providers/bid_item_provider.dart:187

### [RESOLVED] 2026-02-20: M&P enrichment no-op when provider project context is unset
**Status**: FIXED (Session 399).
**Pattern**: `enrichWithMeasurementPayment` returned early when `currentProjectId` was null, causing silent no-op in valid M&P apply flows.
**Prevention**: Resolve matched bid items by id via repository fallback, track touched project ids, and reload/notify safely even without preset provider context.
**Ref**: @lib/features/quantities/presentation/providers/bid_item_provider.dart:293

---

## Archived from _defects-sync.md (2026-02-21)

### [TEST] 2026-02-21: SyncProvider Test Mock Construction Fails with Null DatabaseService
**Status**: RESOLVED in Session 426.
**Symptom**: `test/features/sync/presentation/providers/sync_provider_test.dart` fails before assertions with `type 'Null' is not a subtype of type 'DatabaseService'`, followed by `LateInitializationError` on `syncProvider`.
**Root Cause (observed)**: Test `MockSyncService` instantiation path is incompatible with current `SyncService` constructor expectations for `DatabaseService`.
**Impact**: Previously caused sync provider suite failures and contributed to non-green full-repo runs.
**Prevention/Fix Direction**: Keep test doubles aligned with non-null constructor contract and initialize test DB/FFI in setup.
**Ref**: @test/features/sync/presentation/providers/sync_provider_test.dart:7,99

---

## Archived from _defects-pdf.md (2026-02-20, Session 403)

### [DATA] 2026-02-16: CropUpscaler numChannels Mismatch Causes Red Background
**Pattern**: `img.Image()` defaults to `numChannels: 3` (RGB). When input crop is 1-channel grayscale (from `convert(numChannels: 1)`), the `image` package reads `.g=0`, `.b=0` from 1-channel pixels, so white (255) becomes `(r=255,g=0,b=0)` = pure red. `compositeImage` with `a=255` replaces destination entirely. Every upscaled cell crop sent to Tesseract had red background.
**Prevention**: Always match `numChannels` when creating canvas images for compositing. Test with 1-channel inputs, not just default 3-channel.
**Ref**: @lib/features/pdf/services/extraction/shared/crop_upscaler.dart:71

---

## Archived from _defects-pdf.md (2026-02-19, Session 381)

### [DATA] 2026-02-15: ColumnDef.copyWith Cannot Set headerText to Null
**Pattern**: `copyWith(headerText: null)` uses `headerText ?? this.headerText`, so null is indistinguishable from "not provided". Validation that needs to revert a semantic to null silently keeps the old value.
**Prevention**: Use sentinel pattern (`Object? headerText = _sentinel`) in copyWith for nullable fields. Test that `copyWith(headerText: null)` actually produces null.
**Ref**: @lib/features/pdf/services/extraction/models/column_map.dart:28-40

---

## Archived from _defects-pdf.md (2026-02-20, Session 399)

### [DATA] 2026-02-19: _correctEdgePosForLineDrift Returns Inset in Wrong Coordinate Frame
**Status**: FIXED (Session 381). Drift correction removed, baselineInset updated. Pipe artifacts: 0.
**Ref**: @lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:708-756

### [RESOLVED] 2026-02-19: Tesseract Produced Garbage for Items 64, 74, 75, 77 — Grid Line Fringe + baselineInset Floor
**Status**: FIXED (Session 383). All 4 items recovered. 131/131 GT matched, 0 bogus.
**Root cause (confirmed)**: Two-layer failure:
1. `_scanRefinedInsetAtProbe` had `plannedDepth = w+aa+3 = 6` for width-2 horizontal lines on page 3. Anti-aliased fringe extended exactly 6 dark pixels -> scan returned null -> fell back to `baselineInset = 3` (insufficient to clear fringe).
2. Line 745 used `baselineInset` as a FLOOR on all scan results, overriding dynamic measurements.
3. Residual fringe pixels, after 2.3x upscaling, became a prominent dark bar. PSM 7 read the bar as "al"/"ot"/"re"/"or" instead of the actual digits above.
**Fix**: Increased `plannedDepth` to `w+aa+5`. Removed `baselineInset` floor (line 745). Scan results now trusted.
**Ref**: @lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:724-744

### [DATA] 2026-02-19: Items 29, 113 bid_amount — Text Touches Grid Line Fringe Zone
**Pattern**: Right vertical lines on pages 1, 4 are width=5 (thickest in document). Bid amount text ($7,026.00, $2,000.00) physically extends into the grid line fringe zone. No pixel-threshold inset can distinguish fringe from content. Diagnostic images show last `0` half-cut.
**Prevention**: OpenCV morphological line removal (`adaptiveThreshold` + `morphologyEx(MORPH_OPEN)`) can erase grid lines by shape without touching adjacent text.
**Status**: Open. Pre-existing (items were empty/null in committed HEAD). OpenCV integration planned for next session.
**Ref**: Diagnostic images `page_1_row_24_col_5_*.png`, `page_4_row_27_col_5_*.png`

---

## Archived from _defects-pdf.md (2026-02-18, Session 375)

### [DATA] 2026-02-15: Blind Position Fallback Maps Margins as Data Columns
**Pattern**: `_mapColumnSemantics` in row_parser used `standardOrder[i]` fallback when headerText is null, mapping narrow margin columns (5.3% width page-edge gutters) as 'itemNumber'. Grid creates 8 columns from 7 lines but 2 are margins.
**Prevention**: Never use position-based semantic guessing. Column detector should provide all semantics via header OCR + anchor-relative inference + content validation. Row parser should skip null-header columns.
**Ref**: @lib/features/pdf/services/extraction/stages/row_parser_v2.dart:400-418
**Archive note**: Superseded by Row Parser V3 migration and V2 parser removal in Session 375.

---

## Archived from _defects-pdf.md (2026-02-18, Session 373)

### [DATA] 2026-02-15: img.getLuminance() Fails on 1-Channel Images
**Pattern**: `img.getLuminance(pixel)` computes `0.299*r + 0.587*g + 0.114*b`. On 1-channel images (from `convert(numChannels: 1)`), `pixel.g=0` and `pixel.b=0`, so white pixel (255) returns luminance 76 — below 128 "dark" threshold. Every pixel appears dark.
**Prevention**: Use `pixel.r` directly for single-channel images, not `getLuminance()`. Always verify pixel reading functions handle single-channel images from the `image` package.
**Ref**: @lib/features/pdf/services/extraction/stages/grid_line_detector.dart:224-229

---

## Archived from _defects-pdf.md (2026-02-17, Session 362)

### [CONFIG] 2026-02-14: PSM=6 (Single Block) Destroys Table OCR on Full Pages
**Pattern**: Default `OcrConfigV2(psmMode: 6)` tells Tesseract to treat entire page as one text block, disabling column detection. On table-heavy pages, reads across all 6 columns producing garbage. Also `pageSegMode` getter missing `case 4`.
**Prevention**: Use PSM 7 (singleLine) per cell crop for table pages. Use PSM 4 (singleColumn) for non-table pages.
**Ref**: @lib/features/pdf/services/extraction/ocr/tesseract_config_v2.dart:75,84-98

### [DATA] 2026-02-15: Region Detector Ignores Grid Line Data — 0 Regions on Grid Pages
**Pattern**: `RegionDetectorV2.detect()` only accepts `ClassifiedRows` and requires `RowType.header` rows to create table regions. Cell-cropped OCR fragments header text so row classifier finds 0 headers → 0 regions → 0 items.
**Prevention**: Region detection should use grid line data as primary signal. Grid pages with `hasGrid=true` should produce table regions regardless of header detection.
**Ref**: @lib/features/pdf/services/extraction/stages/region_detector_v2.dart:41-43,80

---

## Archived from _defects-pdf.md (2026-02-15, Session 349)

### [DATA] 2026-02-14: ResultConverter Uses Substring Matching Instead of StageNames Constants
**Pattern**: `ResultConverter` checked `stageName.contains('page_renderer')` which didn't match the actual `StageNames.pageRendering` value (`page_rendering`). OCR detection silently broken for V2 pipeline.
**Prevention**: Always use `StageNames.*` constants for stage name comparisons. Never use substring/contains matching on stage names.
**Ref**: @lib/features/pdf/services/extraction/pipeline/result_converter.dart

---

## Archived from _defects-pdf.md (2026-02-15, Session 348)

### [DATA] 2026-02-14: QualityReport.isValid Rejects Valid Attempt-Exhausted Reports
**Pattern**: `isValid` used hardcoded score-to-status mapping without considering `reExtractionAttempts`. Score 0.55 at attempt 2 should be `partialResult` (not `reExtract`), but `isValid` always expected `reExtract` for 0.45-0.64 range.
**Prevention**: Centralize threshold logic in `QualityThresholds.statusForScore()` — never duplicate score-to-status mapping inline.
**Ref**: @lib/features/pdf/services/extraction/shared/quality_thresholds.dart

### [DATA] 2026-02-14: Divergent Threshold Constants Across 4 Files
**Pattern**: Score thresholds 0.85/0.65/0.45 were hardcoded independently in `quality_report.dart`, `quality_validator.dart`, `extraction_metrics.dart`, and pipeline exit logic. Changes to one file didn't propagate.
**Prevention**: Use `QualityThresholds.*` constants as single source of truth for all threshold comparisons.
**Ref**: @lib/features/pdf/services/extraction/shared/quality_thresholds.dart

---

## Archived from _defects-pdf.md (2026-02-15, Session 347)

### [DATA] 2026-02-06: Empty Uint8List Passes Null Guards But Crashes img.decodeImage()
**Pattern**: Native text path creates `Uint8List(0)` per page. Code checks `if (bytes == null)` but empty list is not null — `img.decodeImage()` throws RangeError on empty bytes instead of returning null.
**Prevention**: Always check `bytes == null || bytes.isEmpty` before passing to image decoders
**Ref**: @lib/features/pdf/services/table_extraction/cell_extractor.dart:761, :920

## Archived from _defects-pdf.md (2026-02-14, Session 340)

### [DATA] 2026-02-06: OCR Used on Digital PDFs Without Trying Native Text First
**Pattern**: `importBidSchedule()` always renders PDF to images and runs Tesseract OCR, even on digital PDFs with extractable native text.
**Prevention**: Always try native text extraction first, fall back to OCR only when `needsOcr()` returns true
**Ref**: @lib/features/pdf/services/pdf_import_service.dart:694
**Archive note**: Superseded by OCR-only pipeline decision — native text extraction abandoned due to CMap corruption across PDFs.

## Archived from _defects-pdf.md (2026-02-14, Session 338)

### [DATA] 2026-02-06: Adaptive Thresholding Destroys Clean PDF Images
**Pattern**: Unconditional binarization converts 300 DPI grayscale to binary, destroying 92% of image data
**Prevention**: Only apply binarization to noisy scans/photos; clean PDF renders need grayscale + contrast only
**Ref**: @lib/features/pdf/services/ocr/image_preprocessor.dart:152-177

### [DATA] 2026-02-04: Substring Keyword Matching Causes False Positives
**Pattern**: Using `String.contains()` for keyword matching allows substring false positives
**Prevention**: Use word-boundary matching (RegExp `\bKEYWORD\b`) for single-word patterns
**Ref**: @lib/features/pdf/services/table_extraction/table_locator.dart:299

### [DATA] 2026-02-04: else-if Chain Blocks Multi-Category Keyword Matching
**Pattern**: Using `else if` chain in keyword matching prevents independent elements from matching different categories
**Prevention**: Use independent `if` + `continue` pattern
**Ref**: @lib/features/pdf/services/table_extraction/header_column_detector.dart:228

---

### [DATA] 2026-02-08: Per-Page Column Detection Hardcodes Empty Header Elements — FIXED (Session 321)
**Pattern**: `_detectColumnsPerPage()` passes `headerRowElements: <OcrElement>[]` for every page, so continuation pages never get header-based column detection — always falling to 0% confidence fallback.
**Prevention**: When adding per-page processing loops, verify inputs aren't hardcoded empty. Extract header elements per-page using repeated header Y positions.
**Fix**: Added `_extractHeaderElementsForPage()` with 3-strategy layered approach + `globalHeaderElements` parameter. Replaced binary confidence comparison with structural scoring.
**Ref**: @lib/features/pdf/services/table_extraction/table_extractor.dart:1237

---

### [ASYNC] 2026-01-21: Async Context Safety (archived 2026-02-08)
**Pattern**: Using context after await without mounted check
**Prevention**: Always `if (!mounted) return;` before setState/context after await
**Ref**: @lib/features/entries/presentation/screens/entry_wizard_screen.dart

### [ASYNC] 2026-01-19: Provider Returned Before Async Init (archived 2026-02-06)
**Pattern**: Returning Provider from `create:` before async init completes
**Prevention**: Add `isInitializing` flag, show loading state until false
**Ref**: @lib/main.dart:365-378

### [E2E] 2026-01-25: Silent Skip with if(widget.exists) (archived 2026-02-06)
**Pattern**: Using `if (widget.exists) { ... }` silently skips when widget not visible
**Prevention**: Use `waitForVisible()` instead - let it fail explicitly if widget should exist

### [E2E] 2026-01-24: Test Helper Missing scrollTo() (archived 2026-02-06)
**Pattern**: Calling `$(finder).tap()` on widgets below the fold
**Prevention**: Always `$(finder).scrollTo()` before `$(finder).tap()` for form fields

### [FLUTTER] 2026-01-18: Deprecated Flutter APIs (archived 2026-02-04)
**Pattern**: Using deprecated APIs (WillPopScope, withOpacity)
**Prevention**: `WillPopScope` -> `PopScope`; `withOpacity(0.5)` -> `withValues(alpha: 0.5)`

### [CONFIG] 2026-01-14: flutter_secure_storage v10 Changes (archived 2026-02-04)
**Pattern**: Using deprecated `encryptedSharedPreferences` option
**Prevention**: Remove option - v10 uses custom ciphers by default, auto-migrates data

## Archived Active Patterns (2026-02-05 trim)

These were active patterns archived when _defects.md was trimmed from 15 to 7.

### [E2E] 2026-01-23: TestingKeys Defined But Not Wired (archived 2026-02-05)
**Pattern**: Adding key to TestingKeys class but not assigning to widget
**Prevention**: After adding TestingKey, immediately wire: `key: TestingKeys.myKey`

### [E2E] 2026-01-22: Patrol CLI Version Mismatch (archived 2026-02-05)
**Pattern**: Upgrading patrol package without upgrading patrol_cli
**Prevention**: patrol v4.x requires patrol_cli v4.x - run `dart pub global activate patrol_cli`

### [E2E] 2026-01-18: dismissKeyboard() Closes Dialogs (archived 2026-02-05)
**Pattern**: Using `h.dismissKeyboard()` (pressBack) inside dialogs
**Prevention**: Use `scrollTo()` to make buttons visible instead of pressBack

### [E2E] 2026-01-17: Git Bash Silent Output (archived 2026-02-05)
**Pattern**: Running Flutter/Patrol commands through Git Bash loses stdout/stderr
**Prevention**: Always use PowerShell: `pwsh -File run_patrol_batched.ps1`

### [DATA] 2026-01-20: Unsafe Collection Access (archived 2026-02-05)
**Pattern**: `.first` on empty list, `firstWhere` without `orElse`
**Prevention**: Use `.where((e) => e.id == id).firstOrNull` pattern

### [DATA] 2026-01-16: Seed Version Not Incremented (archived 2026-02-05)
**Pattern**: Updating form JSON definitions without incrementing seed version
**Prevention**: Always increment `seedVersion` in seed data when modifying form JSON

### [DATA] 2026-01-15: Missing Auto-Fill Source Config (archived 2026-02-05)
**Pattern**: Form field JSON missing `autoFillSource` property
**Prevention**: Include `autoFillSource` for fields that should auto-fill; increment seed version

### [CONFIG] 2026-01-19: Supabase Instance Access (archived 2026-02-05)
**Pattern**: Accessing Supabase.instance without checking configuration
**Prevention**: Always check `SupabaseConfig.isConfigured` before accessing Supabase.instance

## Archived Active Patterns (2026-01)

These were active patterns that didn't make the top 15 in defects.md.

### [E2E] 2026-01-16: Inadequate E2E Test Debugging
**Pattern**: Declaring test success based on partial output without analyzing full logs
**Prevention**: Search logs for `TimeoutException`, `hanging`; check duration (>60s = likely hanging)

### [E2E] 2026-01-15: Test Delays
**Pattern**: Using hardcoded `Future.delayed()` in tests
**Prevention**: Use condition-based waits: `await $.waitUntilVisible(finder);`

### [E2E] 2026-01-14: Hardcoded Test Widget Keys
**Pattern**: Using `Key('widget_name')` directly in widgets and tests
**Prevention**: Always use `TestingKeys` class from `lib/shared/testing_keys/testing_keys.dart`

### [E2E] 2026-01-13: Missing TestingKeys for Dialog Buttons
**Pattern**: UI dialogs missing TestingKeys on action buttons
**Prevention**: When creating dialogs with action buttons, always add TestingKeys

### [E2E] 2026-01-12: E2E Tests Missing Supabase Credentials
**Pattern**: Running patrol tests without SUPABASE_URL and SUPABASE_ANON_KEY
**Prevention**: Always use `run_patrol.ps1` which loads from `.env.local`

### [E2E] 2026-01-11: Gradle File Lock on Test Results
**Pattern**: Gradle creates .lck files preventing subsequent test runs
**Prevention**: Kill stale Java/Gradle processes; clean `build/app/outputs/androidTest-results`

### [E2E] 2026-01-10: Raw app.main() in Patrol Tests
**Pattern**: Using `app.main()` directly without the helper pattern
**Prevention**: Use `PatrolTestConfig.createHelpers($, 'test_name')`, `h.launchAppAndWait()`

### [E2E] 2026-01-09: Repeated Test Runs Corrupt App State
**Pattern**: Running E2E tests repeatedly without resetting device/app state
**Prevention**: Reset app state: `adb shell pm clear com.fvconstruction.construction_inspector`

### [E2E] 2026-01-08: Keyboard Covers Text Field After Tap
**Pattern**: Tapping text field opens keyboard, which covers the field
**Prevention**: After tapping text field, call `scrollTo()` again before `enterText()`

### [E2E] 2026-01-07: assertVisible Without Scroll
**Pattern**: Calling `h.assertVisible(key, msg)` on elements below the fold
**Prevention**: Always `$(key).scrollTo()` before `h.assertVisible()` for below-fold elements

### [E2E] 2026-01-06: .exists Doesn't Mean Hit-Testable
**Pattern**: Using `.exists` to check if widget is ready before `.tap()`
**Prevention**: `.exists` is true for widgets below fold; use `safeTap(..., scroll: true)`

### [DATA] 2026-01-05: Rethrow in Callbacks
**Pattern**: Using `rethrow` in `.catchError()` or `onError` callbacks
**Prevention**: Use `throw error` in callbacks, `rethrow` only in catch blocks

---

## Fixed Defects (2026-01)

### 2026-01-21: PatrolIntegrationTester.takeScreenshot() Doesn't Exist [FIXED]
**Issue**: Patrol tests fail - `takeScreenshot` isn't defined for PatrolIntegrationTester
**Fix**: Use graceful fallback pattern; screenshot is `$.native.takeScreenshot()` or skip

### 2026-01-21: Patrol openApp() Empty Package Name [FIXED]
**Issue**: `openApp()` passed empty package name
**Fix**: Always pass explicit appId: `$.native.openApp(appId: 'com.package.name')`

### 2026-01-21: Test Orchestrator Version Doesn't Exist [FIXED]
**Issue**: Could not find androidx.test:orchestrator:1.5.2
**Fix**: Use version 1.6.1 (latest)

### 2026-01-21: Patrol Tests Fail Before App Initializes [FIXED]
**Issue**: Tests couldn't find widgets after app.main()
**Fix**: Add delay after pumpAndSettle for apps with async init

### 2026-01-20: ProjectProvider Unsafe firstWhere [FIXED]
**Issue**: .first on empty list throws, unchecked firstWhere throws
**Fix**: Use .where().firstOrNull pattern across all providers

### 2026-01-20: Hardcoded Supabase Credentials [FIXED]
**Issue**: Supabase URL and anon key committed to git
**Fix**: Use String.fromEnvironment(), added isConfigured check

### 2026-01-20: copyWithNull Test Failures [FIXED]
**Issue**: Tests referenced copyWithNull() but models only have copyWith()
**Fix**: Removed failing tests from repository test files

### 2026-01-21: Patrol Tests Build but Execute 0 Tests [FIXED]
**Issue**: 69 tests built but 0 executed
**Fix**: Target `integration_test/test_bundle.dart` (auto-generated), not manual aggregator

### 2026-01-21: Patrol CLI "Failed to read Java version" [FIXED]
**Issue**: Patrol couldn't read Java version on Windows
**Fix**: Install Android SDK Command-line Tools from SDK Manager

### 2026-01-21: Patrol MainActivityTest.java Outdated API [FIXED]
**Issue**: PatrolTestRule API doesn't exist in Patrol 3.20.0
**Fix**: Use Parameterized JUnit pattern from Patrol example

### 2026-01-21: Seed Data Missing NOT NULL Timestamps [FIXED]
**Issue**: NOT NULL constraint failed on entry_personnel.created_at
**Fix**: Added timestamps to all insert operations

### 2026-01-21: SyncService Crashes When Supabase Not Configured [FIXED]
**Issue**: App crashes accessing Supabase.instance without credentials
**Fix**: Made _supabase nullable, check SupabaseConfig.isConfigured

### 2026-01-21: Gradle Configuration Cache Incompatible [FIXED]
**Issue**: Configuration cache error with Flutter
**Fix**: Disable org.gradle.configuration-cache

### 2026-01-21: Patrol Test Hangs at Gradle Config [FIXED]
**Issue**: Circular dependency in build.gradle.kts
**Fix**: Remove evaluationDependsOn block

### 2026-01-21: Stale Compilation Cache [FIXED]
**Issue**: False compilation errors after code changes
**Fix**: Run `flutter clean && flutter pub get`

### 2026-01-21: Invalid rethrow in catchError [FIXED]
**Issue**: `rethrow` used in .catchError() callback
**Fix**: Use `throw error` instead of `rethrow` in callbacks

### 2026-01-21: Router Accesses Supabase.instance Without Check [FIXED]
**Issue**: Router crashed without Supabase config
**Fix**: Check SupabaseConfig.isConfigured before Supabase.instance

---

## Unfixed but Low Priority

### 2026-01-21: GoTrueClient Mock Signature Mismatch
**Issue**: Mock missing captchaToken, channel parameters
**Fix Needed**: Update auth_service_test.dart mocks

### 2026-01-21: Missing TestWidgetsFlutterBinding
**Issue**: SyncService tests crash without binding
**Fix Needed**: Add TestWidgetsFlutterBinding.ensureInitialized()

### 2026-01-21: Wrong Package Name in Test Helper
**Issue**: test_sorting.dart imports construction_app
**Fix Needed**: Change to construction_inspector

### 2026-01-21: Mock Repository Method Names Mismatch
**Issue**: Mock methods don't match test expectations
**Fix Needed**: Rename mock methods or use mocktail
