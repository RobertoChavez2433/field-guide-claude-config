# Defects Log

Track Claude's mistakes to prevent repetition. Read before every session.

## Format
### YYYY-MM-DD: [Title]
**Issue**: What went wrong
**Root Cause**: Why
**Prevention**: How to avoid

---

## Logged Defects

### 2026-01-19: Async in dispose()
**Issue**: Called async `_saveIfEditing()` in `dispose()` - context already deactivated
**Fix**: Use `WidgetsBindingObserver.didChangeAppLifecycleState` for lifecycle saves
**Ref**: @lib/features/entries/presentation/screens/home_screen.dart:154-166

### 2026-01-19: Test sort order with same timestamps
**Issue**: Test expected specific sort order but all entries had same `updatedAt`
**Fix**: Use different timestamps in test data when testing sort behavior

### 2026-01-20: Context Used After Async Without Mounted Check
**Issue**: Entry wizard and report screen use context.read() after async gaps
**Root Cause**: Auto-save triggered by lifecycle observer after disposal
**Prevention**: Always check mounted before context after await
**Ref**: @lib/features/entries/presentation/screens/entry_wizard_screen.dart:143

### 2026-01-20: Silent Failure on Entry Creation
**Issue**: Entry creation failure doesn't notify user
**Root Cause**: No error handling in else branch of null check
**Prevention**: Always handle both success and failure branches
**Ref**: @lib/features/entries/presentation/screens/entry_wizard_screen.dart:217

### 2026-01-20: ProjectProvider Unsafe firstWhere [FIXED]
**Issue**: selectProject() and toggleActive() use unsafe .first and unchecked firstWhere
**Root Cause**: .first on empty list throws, unchecked firstWhere throws
**Prevention**: Always use .where().firstOrNull pattern instead of firstWhere without orElse
**Fix Applied**: Replaced all unsafe firstWhere and .first calls with .where().firstOrNull pattern across all providers
**Files Fixed**:
- project_provider.dart (selectProject, toggleActive, getProjectById)
- entry_quantity_provider.dart (removeQuantity, getQuantityById)
- bid_item_provider.dart (getBidItemByNumber)
- contractor_provider.dart (primeContractor getter)
- personnel_type_provider.dart (getTypeByShortCode, getTypeByName)
- photo_provider.dart (getPhotoById)
**Ref**: @lib/features/projects/presentation/providers/project_provider.dart:117-130,235-262

### 2026-01-20: Hardcoded Supabase Credentials [FIXED]
**Issue**: Supabase URL and anon key committed to git
**Root Cause**: Config stored as const instead of environment variables
**Prevention**: Use --dart-define or environment variables
**Fix Applied**:
- Changed SupabaseConfig to use String.fromEnvironment()
- Added isConfigured check to gracefully handle unconfigured state
- Updated main.dart to skip Supabase initialization if not configured
- Made AuthService.client nullable with proper error handling
- Added check in SyncService.syncAll() to skip if not configured
- Created .env.example with documentation
- Updated README.md with configuration instructions
**Files Fixed**:
- lib/core/config/supabase_config.dart (use environment variables)
- lib/main.dart (conditional initialization)
- lib/features/auth/services/auth_service.dart (nullable client)
- lib/services/sync_service.dart (configuration check)
- .env.example (created)
- README.md (updated with instructions)
**Ref**: @lib/core/config/supabase_config.dart:11-21

### 2026-01-20: Sync Queue Silent Deletion
**Issue**: Items deleted after max retries without persistent record
**Root Cause**: No dead letter queue for permanently failed syncs
**Prevention**: Always preserve failed operations for manual review
**Ref**: @lib/services/sync_service.dart:283-291

### 2026-01-20: Migration ALTER TABLE Without Error Handling
**Issue**: v7→v8 migration crashes if columns already exist
**Root Cause**: SQLite doesn't support IF NOT EXISTS for columns
**Prevention**: Check column existence before ALTER TABLE
**Ref**: @lib/core/database/database_service.dart:435-443

### 2026-01-20: _pushBaseData Queries All Tables Every Sync
**Issue**: Makes 11 remote queries EVERY sync even after initial seed
**Root Cause**: No flag to track "initial seed complete"
**Prevention**: Use metadata table to track initialization state
**Ref**: @lib/services/sync_service.dart:302-473

### 2026-01-20: copyWithNull Test Failures [FIXED]
**Issue**: Tests for Project and Location repositories failing due to missing copyWithNull method
**Root Cause**: Tests referenced copyWithNull() but models only have copyWith() - likely legacy test code
**Prevention**: Ensure test expectations match actual model API; remove unused test cases
**Fix Applied**: Removed the failing copyWithNull tests from both repository test files
**Files Fixed**:
- test/features/projects/data/repositories/project_repository_test.dart (removed test at line 574-590)
- test/features/locations/data/repositories/location_repository_test.dart (removed test at line 628-643)
**Ref**: @test/features/projects/data/repositories/project_repository_test.dart, @test/features/locations/data/repositories/location_repository_test.dart

### 2026-01-21: Patrol Tests Build but Execute 0 Tests
**Issue**: 69 Patrol integration tests built successfully but Android Test Orchestrator reported "0 tests executed"
**Root Cause**: patrol.yaml targeted `integration_test/patrol/test_bundle.dart` (manual aggregator) instead of `integration_test/test_bundle.dart` (auto-generated)
**Why It Fails**: Manual aggregator has 0 `patrolTest()` declarations - just imports and calls `main()` on test modules. Android's PatrolJUnitRunner can't discover tests inside imported modules.
**Prevention**:
- ALWAYS target Patrol CLI's auto-generated `integration_test/test_bundle.dart`
- Auto-generated bundle has proper infrastructure: test explorer, PatrolAppService, group wrapping
- Do NOT create manual test aggregators - Patrol handles bundling automatically
**Fix**: Change patrol.yaml target to `integration_test/test_bundle.dart`
**Ref**: @patrol.yaml:8, @integration_test/test_bundle.dart

### 2026-01-21: Patrol CLI "Failed to read Java version" on Windows
**Issue**: Patrol test command fails with "Error: Failed to read Java version" even though Java is installed
**Root Cause**: Patrol CLI reads Java from `flutter doctor` output. Without Android SDK cmdline-tools installed, flutter doctor doesn't show Java version under Android toolchain.
**Prevention**:
- Ensure Android SDK Command-line Tools is installed via Android Studio SDK Manager (Tools → SDK Manager → SDK Tools tab)
- Run `flutter doctor --android-licenses` to accept licenses
- Verify `flutter doctor -v` shows "Java binary at:" under Android toolchain
**Fix**: Install "Android SDK Command-line Tools (latest)" from SDK Manager
**Ref**: https://github.com/leancodepl/patrol/issues/2160

### 2026-01-21: Patrol MainActivityTest.java Outdated API Pattern
**Issue**: QA agent created MainActivityTest.java with `PatrolTestRule` API that doesn't exist in Patrol 3.20.0
**Root Cause**: Using outdated documentation/patterns - PatrolTestRule was removed in newer Patrol versions
**Prevention**:
- ALWAYS check the Patrol example in the installed package: `~/.pub-cache/hosted/pub.dev/patrol-X.X.X/example/android/app/src/androidTest/`
- Patrol 3.20.0+ requires `@RunWith(Parameterized.class)` pattern, NOT `@RunWith(PatrolJUnitRunner.class)`
- The correct pattern uses `@Parameters` method calling `instrumentation.listDartTests()`
**Fix**: Use Parameterized JUnit pattern from Patrol example
**Ref**: @android/app/src/androidTest/java/com/fvconstruction/construction_inspector/MainActivityTest.java

### 2026-01-21: Seed Data Missing NOT NULL Timestamps [FIXED]
**Issue**: Patrol tests crash with `DatabaseException(NOT NULL constraint failed: entry_personnel.created_at)`
**Root Cause**: SeedDataService.seedDatabase() INSERT statements for entry_personnel and entry_quantities missing created_at/updated_at columns
**Why It Fails**: Database schema has NOT NULL constraints on these columns
**Prevention**:
- ALWAYS check database schema for NOT NULL columns before writing INSERT statements
- Include created_at/updated_at in ALL insert operations for timestamped tables
**Fix Applied**:
- Added `created_at: now, updated_at: now` to entry_personnel insert
- Added timestamps to all 12+ entry_quantities insert locations
**Files Fixed**:
- lib/core/database/seed_data_service.dart (lines 473-730)
**Ref**: @lib/core/database/seed_data_service.dart:473

### 2026-01-21: SyncService Crashes When Supabase Not Configured [FIXED]
**Issue**: App crashes with "You must initialize the supabase instance before calling Supabase.instance"
**Root Cause**: SyncService constructor accessed Supabase.instance.client unconditionally even when no credentials configured
**Why It Fails**: Tests run without Supabase environment variables, but SyncService tries to access singleton
**Prevention**:
- ALWAYS check SupabaseConfig.isConfigured before accessing Supabase.instance
- Make Supabase client fields nullable when configuration is optional
**Fix Applied**:
- Made _supabase field nullable: `final SupabaseClient? _supabase`
- Conditional initialization: `_supabase = SupabaseConfig.isConfigured ? Supabase.instance.client : null`
- Used force-unwrap `_supabase!` protected by existing isConfigured guard in syncAll()
**Files Fixed**:
- lib/services/sync_service.dart (lines 77, 107, 338-517)
**Ref**: @lib/services/sync_service.dart:107

### 2026-01-21: Gradle Configuration Cache Incompatible with Flutter [FIXED]
**Issue**: Patrol build fails with "Configuration cache state could not be cached" error
**Root Cause**: org.gradle.configuration-cache=true in gradle.properties incompatible with Flutter's Gradle plugin
**Why It Fails**: Flutter's DependencyVersionChecker and Android Gradle plugin have serialization issues with Kotlin lazy delegates
**Prevention**:
- Do NOT enable org.gradle.configuration-cache for Flutter projects (as of 2026)
- Test Gradle changes with `flutter build apk --config-only` before full build
**Fix Applied**:
- Commented out `org.gradle.configuration-cache=true` in gradle.properties
**Files Fixed**:
- android/gradle.properties (line 9)
**Ref**: @android/gradle.properties

### 2026-01-21: Patrol Test Hangs at Gradle Config Phase [FIXED]
**Issue**: `patrol test --verbose` hung indefinitely at `flutter build apk --config-only` step
**Root Cause**: Gradle circular dependency - `android/build.gradle.kts` lines 18-20 had `subprojects { evaluationDependsOn(":app") }` which creates a deadlock during configuration phase
**Why It Fails**: `:app` IS a subproject, so it waits for itself to finish configuration, causing infinite wait
**Prevention**:
- NEVER use `evaluationDependsOn` in subprojects block for single-module Flutter projects
- Flutter's Gradle plugin handles inter-project dependencies automatically
- Test Gradle configuration with `flutter build apk --config-only` before full patrol test
**Fix Applied**:
- Deleted circular dependency block from android/build.gradle.kts
- Added Gradle optimizations (daemon, parallel, caching) to gradle.properties
- Changed gradle-wrapper.properties from -all.zip to -bin.zip (faster downloads)
**Files Fixed**:
- android/build.gradle.kts (deleted lines 18-20)
- android/gradle.properties (added 9 optimization lines)
- android/gradle/wrapper/gradle-wrapper.properties (changed distribution type)
**Ref**: @android/build.gradle.kts, @.claude/implementation/patrol_fix_plan.md

<!-- Add new defects above this line -->
