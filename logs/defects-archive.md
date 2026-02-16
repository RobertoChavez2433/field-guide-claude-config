# Defects Archive

Historical defects moved from per-feature defect files. Reference only.

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
