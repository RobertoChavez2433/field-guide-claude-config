## Phase 1: Foundation (analysis_options.yaml + pubspec.yaml)

### Sub-phase 1.1: Upgrade flutter_lints to lints Package

**Files:**
- Modify: `pubspec.yaml:129`
- Modify: `analysis_options.yaml:10`

**Agent**: `general-purpose`

#### Step 1.1.1: Replace flutter_lints with lints in pubspec.yaml

Open `pubspec.yaml` and replace line 129:

```yaml
# BEFORE (line 129):
  flutter_lints: ^6.0.0

# AFTER:
  lints: ^5.1.1
```

<!-- WHY: flutter_lints is deprecated. The `lints` package is its successor with stricter defaults. -->
<!-- FROM SPEC: Section 13 Phase 1 - "Upgrade from flutter_lints: ^6.0.0 to current lints package" -->

Also remove the comment block above it (lines 124-128) that references flutter_lints.

#### Step 1.1.2: Update analysis_options.yaml include

Open `analysis_options.yaml` and replace line 10:

```yaml
# BEFORE (line 10):
include: package:flutter_lints/flutter.yaml

# AFTER:
include: package:lints/recommended.yaml
```

#### Step 1.1.3: Run pub get to resolve new dependency

Run: `pwsh -Command "flutter pub get"`
Expected: No errors. The `lints` package resolves successfully.

#### Step 1.1.4: Verify analyze still runs

Run: `pwsh -Command "flutter analyze 2>&1 | Select-Object -First 20"`
Expected: Runs without "package not found" errors. There may be new warnings/errors from stricter rules -- that is expected and will be addressed in Step 1.2.

---

### Sub-phase 1.2: Harden analysis_options.yaml with Strict Rules

**Files:**
- Modify: `analysis_options.yaml` (full rewrite)

**Agent**: `general-purpose`

#### Step 1.2.1: Rewrite analysis_options.yaml with strict rules

Replace the entire contents of `analysis_options.yaml` with:

```yaml
# Field Guide App - Strict Analysis Options
# FROM SPEC: Section 13 Phase 1 - Enable strict lint rules
include: package:lints/recommended.yaml

analyzer:
  errors:
    # FROM SPEC: "Upgrade deprecated_member_use_from_same_package to error"
    deprecated_member_use_from_same_package: error
    # FROM SPEC: "Ensure use_build_context_synchronously is error"
    use_build_context_synchronously: error
    # Treat unused imports as errors to keep imports clean
    unused_import: error
  exclude:
    - "**/*.g.dart"
    - "**/*.freezed.dart"
    - "**/*.mocks.dart"
    - "packages/**"
    - "build/**"

linter:
  rules:
    # FROM SPEC: Section 13 Phase 1 - Enable these rules
    avoid_print: true
    annotate_overrides: true
    unnecessary_overrides: true
    # Additional strict rules from lints/recommended.yaml that we want explicit
    prefer_single_quotes: true
    prefer_const_constructors: true
    prefer_const_declarations: true
    prefer_final_locals: true
    avoid_unnecessary_containers: true
    sized_box_for_whitespace: true
    use_key_in_widget_constructors: true
    # Prevent common bugs
    no_duplicate_case_values: true
    avoid_types_as_parameter_names: true
    empty_catches: true
    null_closures: true
    # Style consistency
    prefer_is_empty: true
    prefer_is_not_empty: true
    unnecessary_new: true
    unnecessary_this: true
    prefer_collection_literals: true
```

<!-- WHY: Clean slate requires zero warnings/errors. These rules catch the most common issues found in 700+ development sessions. -->
<!-- NOTE: We do NOT add `analyzer: plugins: [custom_lint]` yet -- that comes in Phase 3.6 after the lint package is created. -->

#### Step 1.2.2: Run analyze to identify all new violations

Run: `pwsh -Command "flutter analyze 2>&1 | Tee-Object -FilePath '.claude/temp/analyze-phase1.txt'"`
Expected: A list of violations. Capture the output for systematic fixing in Step 1.3.

---

### Sub-phase 1.3: Fix All New Violations from Hardened Rules

**Files:**
- Modify: Multiple files across `lib/` (violations surfaced by new rules)

**Agent**: `general-purpose`

#### Step 1.3.1: Fix unused_import errors

Run: `pwsh -Command "dart fix --apply --code=unused_import"`

<!-- WHY: dart fix can auto-apply safe fixes for unused imports. -->

#### Step 1.3.2: Fix annotate_overrides warnings

Run: `pwsh -Command "dart fix --apply --code=annotate_overrides"`

<!-- FROM SPEC: A16 says 80+ missing @override annotations. dart fix handles this automatically. -->

#### Step 1.3.3: Fix unnecessary_overrides warnings

Run: `pwsh -Command "dart fix --apply --code=unnecessary_overrides"`

#### Step 1.3.4: Fix prefer_const_constructors where applicable

Run: `pwsh -Command "dart fix --apply --code=prefer_const_constructors"`

#### Step 1.3.5: Fix prefer_const_declarations where applicable

Run: `pwsh -Command "dart fix --apply --code=prefer_const_declarations"`

#### Step 1.3.6: Fix remaining auto-fixable violations

Run: `pwsh -Command "dart fix --apply"`

<!-- NOTE: This catches any remaining auto-fixable issues not covered by specific codes above. -->

#### Step 1.3.7: Manual fixes for avoid_print

Search for `print(` calls in `lib/` (not test/) and replace with `Logger.<category>()` calls:

```dart
// BEFORE:
print('some debug message');

// AFTER:
Logger.lifecycle('some debug message');
```

Choose the Logger category based on the file's feature area:
- `lib/features/sync/**` -> `Logger.sync()`
- `lib/features/pdf/**` -> `Logger.pdf()`
- `lib/core/database/**` -> `Logger.db()`
- `lib/features/auth/**` -> `Logger.auth()`
- `lib/services/photo_service.dart` -> `Logger.photo()`
- Other `lib/` files -> `Logger.lifecycle()` or `Logger.ui()` depending on context

Add the Logger import where needed:
```dart
import 'package:construction_inspector/core/logging/logger.dart';
```

<!-- WHY: avoid_print is now enabled. All logging must go through Logger for consistent categorization and file routing. -->
<!-- NOTE: Logger has 11 categories verified at logger.dart:135-176: sync, pdf, db, auth, ocr, nav, ui, photo, lifecycle, bg, error -->

#### Step 1.3.8: Manual fixes for use_build_context_synchronously errors

For any `use_build_context_synchronously` violations that `dart fix` cannot auto-resolve, add mounted guards:

```dart
// BEFORE:
await someAsyncOperation();
context.read<SomeProvider>().doThing();

// AFTER:
await someAsyncOperation();
if (!mounted) return;  // WHY: Context may be invalid after await
context.read<SomeProvider>().doThing();
```

<!-- NOTE: This overlaps with Sub-phase 2.7 (mounted check guards). Fix any that are surfaced here; 2.7 will do a comprehensive audit. -->

#### Step 1.3.9: Manual fixes for deprecated_member_use_from_same_package errors

These are `AppTheme.*` usages within `app_theme.dart` itself or other core/theme files that reference deprecated members internally. Fix only the ones within the `core/theme/` directory -- the bulk AppTheme migration (797 refs across 76 files) is Phase 2.1.

For any self-referencing deprecated usages in `lib/core/theme/app_theme.dart`, redirect to `AppColors.*` directly since `AppTheme.*` constants are just re-exports of `AppColors.*`:

```dart
// BEFORE (inside app_theme.dart):
static const Color someAlias = primaryCyan;  // triggers deprecated_member_use_from_same_package

// AFTER:
static const Color someAlias = AppColors.primaryCyan;
```

#### Step 1.3.10: Verify zero violations

Run: `pwsh -Command "flutter analyze"`
Expected: `No issues found!` (or only the `deprecated_member_use_from_same_package` warnings from AppTheme consumer files, which are Phase 2.1 scope).

**IMPORTANT**: If `deprecated_member_use_from_same_package` is now ERROR severity, the 797 AppTheme usages across 76 files will cause errors. If this blocks analyze from passing, temporarily downgrade to WARNING:

```yaml
analyzer:
  errors:
    deprecated_member_use_from_same_package: warning  # Temporary until Phase 2.1 completes
```

Add a `# TODO: Upgrade to error after Phase 2.1 AppTheme migration` comment. Phase 2.1 will complete the migration and then this gets upgraded back to error.

#### Step 1.3.11: Run tests to verify no regressions

Run: `pwsh -Command "flutter test"`
Expected: All existing tests pass. The analysis_options changes should not affect runtime behavior.

---

## Phase 2: Bulk Violation Cleanup

### Sub-phase 2.1: AppTheme Color Migration (797 refs across 76 files)

**Files:**
- Modify: 76+ files across `lib/` that reference `AppTheme.*` color constants
- No new files created

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.1.1: Understand the migration map

Each `@Deprecated` annotation in `lib/core/theme/app_theme.dart` specifies the exact replacement. The implementing agent MUST read `lib/core/theme/app_theme.dart` (lines 1-130) to see all annotations. The verified migration map from tailor research:

| AppTheme Member | Replacement | Tier |
|-----------------|-------------|------|
| `primaryCyan` | `Theme.of(context).colorScheme.primary` | 1 |
| `primaryBlue` | `Theme.of(context).colorScheme.tertiary` or `AppColors.primaryBlue` | 3 |
| `successGreen` / `statusSuccess` / `success` | `FieldGuideColors.of(context).statusSuccess` | 2 |
| `warningOrange` / `statusWarning` / `warning` | `FieldGuideColors.of(context).statusWarning` | 2 |
| `errorRed` / `statusError` / `error` | `Theme.of(context).colorScheme.error` | 1 |
| `statusInfo` | `Theme.of(context).colorScheme.primary` | 1 |
| `cardBackground` / `surfaceElevated` | `Theme.of(context).colorScheme.surfaceContainerHigh` | 1 |
| `borderColor` / `surfaceHighlight` | `Theme.of(context).colorScheme.outlineVariant` | 1 |
| `surfaceBright` / `surfaceHighest` | `Theme.of(context).colorScheme.surfaceContainerHighest` | 1 |
| `textPrimary` | `Theme.of(context).colorScheme.onSurface` | 1 |
| `textSecondary` | `Theme.of(context).colorScheme.onSurfaceVariant` | 1 |
| `textTertiary` | `FieldGuideColors.of(context).textTertiary` | 2 |
| `textInverse` | `FieldGuideColors.of(context).textInverse` | 2 |

For members NOT marked `@Deprecated` (e.g., `primaryDark`, `primaryLight`, `accentAmber`, `accentOrange`, `accentGold`, `backgroundDark`, `surfaceDark`, `surfaceGlass`, `lightBackground`, `lightSurface`, `lightSurfaceElevated`, `lightSurfaceHighlight`, `lightTextPrimary`, `lightTextSecondary`, `lightTextTertiary`, weather colors, overlay colors, gradients, hc* colors, section colors, etc.) -- these are simple re-exports of `AppColors.*`. Replace `AppTheme.X` with `AppColors.X`.

<!-- WHY: Non-deprecated members are just re-exports. Once all consumers use AppColors directly, the re-exports in AppTheme become dead code. -->
<!-- NOTE: AppTheme.getPrimaryGradient() and AppTheme.getGlassmorphicDecoration() at lines 1731/1755 are NOT deprecated and still used. Leave those references intact. -->
<!-- NOTE: AppTheme.darkTheme, .lightTheme, .highContrastTheme are NOT deprecated. Leave those references intact. -->

#### Step 2.1.2: Migration approach for each file

For each of the 76+ files:

1. **Read the file** to find all `AppTheme.*` references
2. **For each reference**, look up the replacement in the migration map above
3. **Replace the reference** with the correct tier replacement
4. **Update imports**: Add `import 'package:construction_inspector/core/theme/field_guide_colors.dart';` if any Tier 2 replacements were used. Add `import 'package:construction_inspector/core/theme/colors.dart';` if any Tier 3 (`AppColors.*`) replacements were used. Tier 1 (`Theme.of(context).colorScheme.*`) needs no new import.
5. **Remove the AppTheme import** if no non-deprecated AppTheme members remain (i.e., no `getPrimaryGradient`, `getGlassmorphicDecoration`, theme getters)

**IMPORTANT**: Tier 1 and Tier 2 replacements require a `BuildContext`. If the current code uses `AppTheme.primaryCyan` in a context where no `BuildContext` is available (e.g., a static constant, a model class), use the Tier 3 `AppColors.*` equivalent instead. For example:
- `AppTheme.primaryCyan` in a static constant -> `AppColors.primaryCyan`
- `AppTheme.primaryCyan` in a widget build method -> `Theme.of(context).colorScheme.primary`

#### Step 2.1.3: Exemplar transformation -- high-reference-count file

**Exemplar file**: `lib/features/entries/presentation/screens/home_screen.dart` (94 refs per blast-radius.md)

```dart
// BEFORE:
color: AppTheme.primaryCyan,
// AFTER:
color: Theme.of(context).colorScheme.primary,

// BEFORE:
color: AppTheme.textPrimary,
// AFTER:
color: Theme.of(context).colorScheme.onSurface,

// BEFORE:
color: AppTheme.textSecondary,
// AFTER:
color: Theme.of(context).colorScheme.onSurfaceVariant,

// BEFORE:
color: AppTheme.surfaceElevated,
// AFTER:
color: Theme.of(context).colorScheme.surfaceContainerHigh,

// BEFORE:
color: AppTheme.statusSuccess,
// AFTER:
color: FieldGuideColors.of(context).statusSuccess,

// BEFORE:
color: AppTheme.accentAmber,
// AFTER (not deprecated, just a re-export):
color: AppColors.accentAmber,
```

#### Step 2.1.4: Exemplar transformation -- widget with mixed tiers

**Exemplar file**: `lib/features/projects/presentation/screens/project_dashboard_screen.dart` (60 refs)

Same replacement logic. Key nuance: if a `const` widget currently uses `AppTheme.primaryCyan` (a static const), replacing with `Theme.of(context).colorScheme.primary` removes the `const` qualifier. This is correct and expected -- theme-adaptive colors cannot be const.

```dart
// BEFORE:
const Icon(Icons.check, color: AppTheme.statusSuccess)
// AFTER (loses const):
Icon(Icons.check, color: FieldGuideColors.of(context).statusSuccess)
```

#### Step 2.1.5: Execute migration across all 76 files

The implementing agent should:
1. Run `pwsh -Command "flutter analyze 2>&1 | Select-String 'AppTheme'"` to get the current list of files with AppTheme violations
2. Process each file using the migration map
3. Work in batches of ~10 files, running analyze after each batch to verify progress

#### Step 2.1.6: Upgrade deprecated_member_use_from_same_package back to error

After all 797 references are migrated, update `analysis_options.yaml`:

```yaml
analyzer:
  errors:
    deprecated_member_use_from_same_package: error  # Phase 2.1 complete -- all AppTheme refs migrated
```

#### Step 2.1.7: Verify zero AppTheme violations

Run: `pwsh -Command "flutter analyze"`
Expected: No `deprecated_member_use_from_same_package` errors.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass. Color changes are cosmetic -- behavior is unchanged.

---

### Sub-phase 2.2: Supabase Singleton DI Migration (8 violations across 6 files)

**Files:**
- Modify: `lib/shared/datasources/base_remote_datasource.dart:11`
- Modify: `lib/features/auth/di/auth_providers.dart:57`
- Modify: `lib/features/settings/di/consent_support_factory.dart:46`
- Modify: `lib/features/sync/di/sync_providers.dart:58`
- Modify: `lib/features/sync/application/background_sync_handler.dart:49,151`
- Modify: `lib/features/sync/application/sync_orchestrator.dart:225,384`

**Agent**: `backend-data-layer-agent`

#### Step 2.2.1: Audit each violation for fix approach

Read each violation file. The fix depends on how the `Supabase.instance.client` is used:

**Pattern A -- Constructor injection available**: The class already accepts a `SupabaseClient` parameter but some code path bypasses it. Fix: use the injected parameter.

**Pattern B -- Constructor injection needed**: The class constructs `Supabase.instance.client` inline. Fix: add a `SupabaseClient` constructor parameter, wire it through DI from `app_initializer.dart` or the relevant `*_providers.dart`.

**Pattern C -- Background isolate**: `background_sync_handler.dart` runs in a fresh Dart isolate where DI is not available. `Supabase.initialize()` is called manually, then `Supabase.instance.client` is the only way to get the client. This is an **allowed exception** -- add a `// ignore: avoid_supabase_singleton` comment or configure the lint rule to allowlist this file.

<!-- FROM SPEC: Section 4 - "Supabase client: Resolved ONCE in DI root, injected via constructor to all consumers. Supabase.instance.client is a violation anywhere." -->
<!-- NOTE: background_sync_handler.dart is a special case -- it runs in a WorkManager isolate with no access to the DI tree. The lint rule should allowlist this file. -->

#### Step 2.2.2: Fix base_remote_datasource.dart

Read `lib/shared/datasources/base_remote_datasource.dart`. Currently at line 11:
```dart
SupabaseClient get supabase => Supabase.instance.client;
```

Fix: Add constructor injection.

```dart
// BEFORE:
abstract class BaseRemoteDatasource {
  SupabaseClient get supabase => Supabase.instance.client;
}

// AFTER:
abstract class BaseRemoteDatasource {
  final SupabaseClient supabase;
  // WHY: Constructor injection replaces singleton access. Client is resolved once in DI root.
  BaseRemoteDatasource(this.supabase);
}
```

Then audit all concrete subclasses of `BaseRemoteDatasource` to pass through the `SupabaseClient` parameter. Each subclass constructor must call `super(supabaseClient)`. The `SupabaseClient` is already available in the DI tree via `app_initializer.dart` which passes it when constructing datasources.

#### Step 2.2.3: Fix auth_providers.dart

At `lib/features/auth/di/auth_providers.dart:57`, the `AdminRepositoryImpl` is constructed with `Supabase.instance.client` inline inside a provider factory:

```dart
// BEFORE (line 54-60):
ChangeNotifierProvider(
  create: (_) => AdminProvider(
    (companyId) => SupabaseConfig.isConfigured
        ? AdminRepositoryImpl(
            Supabase.instance.client,
            companyId: companyId,
          )
        : const _UnconfiguredAdminRepository(),
  ),
),

// AFTER:
// Add supabaseClient parameter to authProviders function signature:
List<SingleChildWidget> authProviders({
  required AuthService authService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
  required SupabaseClient? supabaseClient,  // WHY: Inject from DI root, no singleton
}) {
  return [
    // ... existing providers ...
    ChangeNotifierProvider(
      create: (_) => AdminProvider(
        (companyId) => supabaseClient != null
            ? AdminRepositoryImpl(
                supabaseClient,
                companyId: companyId,
              )
            : const _UnconfiguredAdminRepository(),
      ),
    ),
  ];
}
```

Then update the call site in `lib/core/di/app_providers.dart` to pass `supabaseClient`:
```dart
...authProviders(
  authService: deps.authService,
  authProvider: deps.authProvider,
  appConfigProvider: deps.appConfigProvider,
  supabaseClient: deps.supabaseClient,  // Already available in AppDependencies
),
```

<!-- NOTE: Verify that AppDependencies has a supabaseClient getter. If not, add one that returns the SupabaseClient from CoreDeps. -->

#### Step 2.2.4: Fix consent_support_factory.dart

At `lib/features/settings/di/consent_support_factory.dart:46`:

```dart
// Read the file to understand its signature, then inject SupabaseClient
// via the factory function parameter instead of Supabase.instance.client.
```

The implementing agent must read the full file, understand how the factory is called, and wire the `SupabaseClient` from the DI tree (through `settings_providers` or `app_providers`).

#### Step 2.2.5: Fix sync_providers.dart

At `lib/features/sync/di/sync_providers.dart:58`:

Similar to auth_providers -- add a `SupabaseClient?` parameter to `SyncProviders.providers()` and pass it from `buildAppProviders()`.

Also fix line 144 (`ConflictAlgorithm.ignore` in sync_providers -- this is a separate sub-phase 2.5 concern but the singleton is the 2.2 fix).

#### Step 2.2.6: Fix sync_orchestrator.dart

At `lib/features/sync/application/sync_orchestrator.dart:225,384`:

The `SyncOrchestrator` class should accept `SupabaseClient` via constructor injection (it likely already does for some code paths). Replace the two inline `Supabase.instance.client` usages with the injected field.

#### Step 2.2.7: Fix background_sync_handler.dart (special case)

At `lib/features/sync/application/background_sync_handler.dart:49,151`:

This is a **top-level function** (`backgroundSyncCallback`) running in a WorkManager isolate. It MUST call `Supabase.initialize()` and then access `Supabase.instance.client` because there is no DI tree in the isolate.

Add lint suppression comments:

```dart
// ignore: avoid_supabase_singleton
final engine = await SyncEngine.createForBackgroundSync(
  database: db,
  supabase: Supabase.instance.client, // ignore: avoid_supabase_singleton
);
```

<!-- WHY: WorkManager isolate has no access to DI tree. This is the documented exception per spec Section 4 / A1 rule. -->

#### Step 2.2.8: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors from these changes.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass. DI wiring changes must not break existing test mocks.

---

### Sub-phase 2.3: DatabaseService() DI Migration (3 violations)

**Files:**
- Modify: `lib/features/pdf/services/pdf_import_service.dart:193`
- Modify: `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart:86`
- Modify: `lib/features/sync/application/background_sync_handler.dart:30`

**Agent**: `backend-data-layer-agent`

#### Step 2.3.1: Fix pdf_import_service.dart

At line 193, `DatabaseService()` is constructed directly. The fix is to inject it via constructor:

```dart
// Read the class to find its constructor, then add DatabaseService parameter.
// The DatabaseService is available in the DI tree via Provider<DatabaseService>.
```

The implementing agent must:
1. Read `lib/features/pdf/services/pdf_import_service.dart`
2. Add `final DatabaseService _dbService;` field
3. Add it to constructor: `PdfImportService({required DatabaseService dbService}) : _dbService = dbService;`
4. Replace `DatabaseService()` at line 193 with `_dbService`
5. Update the construction site in `app_initializer.dart` or the pdf providers to pass `dbService`

#### Step 2.3.2: Fix user_profile_sync_datasource.dart

At `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart:86`:

Same pattern -- add `DatabaseService` as a constructor parameter, replace inline construction.

#### Step 2.3.3: Fix background_sync_handler.dart (special case)

At line 30: `final dbService = DatabaseService();`

This is in the WorkManager isolate callback. Similar to the Supabase case, DatabaseService must be constructed fresh in the isolate because there is no DI tree. Add a lint suppression:

```dart
// ignore: no_direct_database_construction
final dbService = DatabaseService();
```

<!-- WHY: WorkManager isolate starts fresh -- no static state, no Provider tree. DatabaseService must be constructed inline. This is the documented exception. -->

#### Step 2.3.4: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

---

### Sub-phase 2.4: Silent Catch to Logger Calls (20 violations across 9 files)

**Files:**
- Modify: Multiple files (see list below)
- Exclude: `lib/core/logging/logger.dart` (Logger's own catch blocks are intentionally silent to avoid infinite recursion)

**Agent**: `general-purpose`

#### Step 2.4.1: Identify all silent catch blocks

A "silent catch" is a `catch` block that does not contain a `Logger.*` call. The implementing agent must search for catch blocks and audit each one.

Files with known violations (from spec):
- `lib/test_harness.dart:127` -- `catch (_) {}`
- `lib/shared/services/preferences_service.dart:131`
- `lib/shared/providers/base_list_provider.dart:78,115,148,169`
- `lib/shared/providers/paged_list_provider.dart:105,141`
- `lib/services/startup_cleanup_service.dart:39`
- `lib/core/analytics/analytics.dart:43`
- `lib/services/photo_service.dart:28,44,118,179,235,350`
- `lib/services/permission_service.dart:90`
- `lib/shared/utils/field_formatter.dart:57,61`
- `lib/services/image_service.dart:61,81,117`

<!-- NOTE: Exclude lib/core/logging/logger.dart -- Logger's own catch blocks must remain silent to prevent infinite recursion if logging itself fails. -->

#### Step 2.4.2: Add Logger calls to each silent catch

For each violation, add the appropriate Logger category call:

```dart
// BEFORE:
} catch (e) {
  // empty or just rethrow
}

// AFTER:
} catch (e, stack) {
  Logger.error('Failed to [describe operation]', error: e, stack: stack);
}
```

Category selection by file:
| File | Logger Category |
|------|----------------|
| `preferences_service.dart` | `Logger.lifecycle()` |
| `base_list_provider.dart` | `Logger.db()` |
| `paged_list_provider.dart` | `Logger.db()` |
| `startup_cleanup_service.dart` | `Logger.lifecycle()` |
| `analytics.dart` | `Logger.lifecycle()` |
| `photo_service.dart` | `Logger.photo()` |
| `permission_service.dart` | `Logger.lifecycle()` |
| `field_formatter.dart` | `Logger.ui()` |
| `image_service.dart` | `Logger.photo()` |
| `test_harness.dart` | `Logger.lifecycle()` |

Add the Logger import to each file if not already present:
```dart
import 'package:construction_inspector/core/logging/logger.dart';
```

For `catch (_) {}` blocks (like `test_harness.dart:127`), change to `catch (e, stack)` to capture the error object.

#### Step 2.4.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

---

### Sub-phase 2.5: ConflictAlgorithm.ignore Fallback (7 violations outside sync engine)

**Files:**
- Modify: `lib/core/database/database_service.dart:1540`
- Modify: `lib/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart:144`
- Modify: `lib/features/projects/data/services/project_lifecycle_service.dart:68`
- Modify: `lib/features/projects/data/repositories/synced_project_repository.dart:43`
- Modify: `lib/features/projects/data/repositories/project_assignment_repository.dart:57,70`
- Modify: `lib/features/sync/di/sync_providers.dart:144`

**Agent**: `backend-data-layer-agent`

#### Step 2.5.1: Understand the correct pattern

The sync engine at `lib/features/sync/engine/sync_engine.dart:1584-1590` has the correct pattern:

```dart
final rowId = await db.insert(tableName, record,
    conflictAlgorithm: ConflictAlgorithm.ignore);
// WHY: ConflictAlgorithm.ignore returns 0 when insert is silently dropped.
// Must check and fall back to UPDATE to ensure data is written.
if (rowId == 0) {
  await db.update(tableName, record,
      where: 'id = ?', whereArgs: [record['id']]);
}
```

#### Step 2.5.2: Apply the fallback pattern to each violation

For each of the 7 locations, the implementing agent must:

1. Read the surrounding code to understand what table and record are being inserted
2. Capture the return value of `db.insert()` (it returns `int rowId`)
3. Add the `if (rowId == 0)` fallback with an appropriate UPDATE

**Example transformation** (for `synced_project_repository.dart:43`):

```dart
// BEFORE:
await database.insert('synced_projects', {
  'project_id': projectId,
  'enrolled_at': DateTime.now().toUtc().toIso8601String(),
}, conflictAlgorithm: ConflictAlgorithm.ignore);

// AFTER:
final rowId = await database.insert('synced_projects', {
  'project_id': projectId,
  'enrolled_at': DateTime.now().toUtc().toIso8601String(),
}, conflictAlgorithm: ConflictAlgorithm.ignore);
// WHY: ConflictAlgorithm.ignore silently drops the insert on conflict.
// rowId==0 means insert was dropped -- fall back to UPDATE.
if (rowId == 0) {
  await database.update('synced_projects', {
    'enrolled_at': DateTime.now().toUtc().toIso8601String(),
  }, where: 'project_id = ?', whereArgs: [projectId]);
}
```

**IMPORTANT**: For each location, audit whether a silent drop is actually a bug or intentional idempotent behavior. Some usages (like `synced_projects` enrollment) may be intentionally idempotent where a silent drop is acceptable. In those cases, add a Logger call instead of an UPDATE fallback:

```dart
if (rowId == 0) {
  Logger.db('INSERT ignored (already exists): synced_projects project_id=$projectId');
}
```

#### Step 2.5.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

---

### Sub-phase 2.6: TestingKeys Migration (12 hardcoded Key + 41 bypasses)

**Files:**
- Modify: 5 files with hardcoded `Key('...')` in runtime code (12 instances)
- Modify: 12 files with `*TestingKeys.*` bypasses (41 instances)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.6.1: Fix hardcoded Key('...') in runtime code

Search for `Key('` in `lib/` (excluding test/):

```dart
// BEFORE:
key: Key('some_widget_key'),

// AFTER:
key: TestingKeys.someWidgetKey,  // Or the appropriate existing TestingKeys method
```

If no matching `TestingKeys.*` method exists, add one to `lib/shared/testing_keys/testing_keys.dart`:

```dart
static const Key someWidgetKey = Key('some_widget_key');
```

The implementing agent must:
1. Search for `Key('` in `lib/` (not `test/`)
2. For each occurrence, check if a matching `TestingKeys.*` constant exists
3. If yes, replace with `TestingKeys.*`
4. If no, add the key to `TestingKeys` class, then replace

#### Step 2.6.2: Fix TestingKeys bypasses

Search for imports of sub-key files (e.g., `import '...testing_keys/keys/...'`) in `lib/` files. These should import the `TestingKeys` facade instead:

```dart
// BEFORE (bypass -- imports sub-key file directly):
import 'package:construction_inspector/shared/testing_keys/keys/entry_keys.dart';
// Usage: EntryTestingKeys.entryCard

// AFTER (uses facade):
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
// Usage: TestingKeys.entryCard
```

The implementing agent must:
1. Search for `testing_keys/keys/` imports in `lib/` (not test/)
2. Replace with the facade import
3. Update all references from `*TestingKeys.*` to `TestingKeys.*`

#### Step 2.6.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

---

### Sub-phase 2.7: Mounted Check Guards After Async (~10 instances)

**Files:**
- Modify: ~10 files with `context.read`/`context.watch` after `await` without mounted check

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.7.1: Search for violations

The implementing agent must search for patterns where `context.read` or `context.watch` or `Navigator.of(context)` or `ScaffoldMessenger.of(context)` appears after an `await` in the same method, without an intervening `if (!mounted) return;` guard.

Search strategy:
1. Find all `await` calls in `lib/**/presentation/**` files
2. Check if `context` is used after the `await`
3. If yes, check if `if (!mounted) return;` exists between the `await` and the `context` usage
4. If not, add it

#### Step 2.7.2: Apply mounted guard pattern

```dart
// BEFORE:
Future<void> _handleSave() async {
  await repository.save(data);
  context.read<SomeProvider>().refresh();
  Navigator.of(context).pop();
}

// AFTER:
Future<void> _handleSave() async {
  await repository.save(data);
  if (!mounted) return;  // WHY: Widget may have been disposed during async operation
  context.read<SomeProvider>().refresh();
  Navigator.of(context).pop();
}
```

<!-- FROM SPEC: D5 rule - "context use after await needs if (!mounted) return" -->

#### Step 2.7.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No `use_build_context_synchronously` errors (since we set it to error in Phase 1).

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

---

### Sub-phase 2.8: Hardcoded Colors.* Replacement (8 violations)

**Files:**
- Modify: ~8 files in `lib/**/presentation/**` with hardcoded `Colors.*` (excluding `Colors.transparent`)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.8.1: Find all hardcoded Colors.* in presentation

Search for `Colors.` in `lib/**/presentation/**` files, excluding:
- `Colors.transparent` (semantically appropriate, allowed)
- `Colors.white` with opacity (may map to theme tokens)
- `Colors.black` with opacity (may map to theme tokens)

#### Step 2.8.2: Replace with theme tokens

For each hardcoded color, find the appropriate theme token:

| Hardcoded | Replacement |
|-----------|-------------|
| `Colors.red` | `Theme.of(context).colorScheme.error` |
| `Colors.green` | `FieldGuideColors.of(context).statusSuccess` |
| `Colors.orange` | `FieldGuideColors.of(context).statusWarning` |
| `Colors.blue` | `Theme.of(context).colorScheme.primary` |
| `Colors.grey` | `Theme.of(context).colorScheme.onSurfaceVariant` |
| `Colors.white` | `Theme.of(context).colorScheme.onPrimary` or `surface` depending on context |
| `Colors.black` | `Theme.of(context).colorScheme.onSurface` |

The implementing agent must use judgment for each case based on the semantic meaning in context.

#### Step 2.8.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

---

### Sub-phase 2.9: .first to .firstOrNull Audit (~150 across ~67 files)

**Files:**
- Modify: ~67 files with `.first` usage that could throw on empty list

**Agent**: `general-purpose`

#### Step 2.9.1: Audit approach

**IMPORTANT**: Not every `.first` is a violation. Only replace where the list could actually be empty at runtime. The implementing agent must audit each usage:

**KEEP `.first`** when:
- The list is guaranteed non-empty (e.g., immediately after an `if (list.isNotEmpty)` check)
- The list is a hardcoded non-empty literal
- A `firstWhere` with `orElse` is already used

**REPLACE with `.firstOrNull`** when:
- The list comes from a database query (could return empty)
- The list comes from user input or external data
- There is no preceding emptiness check

```dart
// BEFORE (unsafe):
final entry = entries.first;

// AFTER (safe):
final entry = entries.firstOrNull;
if (entry == null) return;  // or handle the empty case
```

<!-- NOTE: .firstOrNull requires import 'package:collection/collection.dart'; which is already a dependency (collection: ^1.19.1 in pubspec.yaml). -->

#### Step 2.9.2: Execute audit in batches

The implementing agent should:
1. Search for `.first` across all `lib/` files (excluding `.firstOrNull`, `.firstWhere`, `.firstWhereOrNull`)
2. For each occurrence, read the surrounding context
3. Decide: keep or replace
4. Work in batches of ~15 files

#### Step 2.9.3: Verify

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors.

Run: `pwsh -Command "flutter test"`
Expected: All tests pass. Some tests may need updating if they relied on `.first` throwing.

---

### Sub-phase 2.10: Future.delayed in Tests (63 across 7 files)

**Files:**
- Modify: 7 test files with `Future.delayed` usage

**Agent**: `qa-testing-agent`

#### Step 2.10.1: Find all Future.delayed in test files

Search for `Future.delayed` in `test/` directory.

#### Step 2.10.2: Replace with proper async test patterns

For each `Future.delayed`, replace with the appropriate async test pattern:

```dart
// BEFORE (bad -- arbitrary delay):
await Future.delayed(Duration(milliseconds: 500));
await tester.pump();

// AFTER (good -- pump until settled):
await tester.pumpAndSettle();
```

```dart
// BEFORE (bad -- waiting for provider update):
await Future.delayed(Duration(seconds: 1));
expect(provider.items.length, 5);

// AFTER (good -- pump to process microtasks):
await tester.pump();
expect(provider.items.length, 5);
```

```dart
// BEFORE (bad -- waiting for async operation):
await Future.delayed(Duration(milliseconds: 200));

// AFTER (good -- use async completion):
await tester.runAsync(() async {
  await someAsyncOperation();
});
await tester.pump();
```

The implementing agent must read each occurrence in context to determine the correct replacement pattern. Some `Future.delayed` may be testing actual delay behavior (e.g., debounce) -- those should be replaced with `fakeAsync`/`clock.elapse()` patterns.

#### Step 2.10.3: Verify

Run: `pwsh -Command "flutter test"`
Expected: All tests pass. Tests should run faster without arbitrary delays.

---

### Sub-phase 2.11: Final Clean Slate Verification

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 2.11.1: Full analyze

Run: `pwsh -Command "flutter analyze"`
Expected: `No issues found!`

#### Step 2.11.2: Full test suite

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

#### Step 2.11.3: Verify deprecated_member_use_from_same_package is error

Confirm `analysis_options.yaml` has:
```yaml
deprecated_member_use_from_same_package: error
```

And analyze still passes (meaning zero deprecated member usages remain).

---

## Phase 3: Custom Lint Package

### Sub-phase 3.1: Package Scaffold

**Files:**
- Create: `fg_lint_packages/field_guide_lints/pubspec.yaml`
- Create: `fg_lint_packages/field_guide_lints/analysis_options.yaml`
- Create: `fg_lint_packages/field_guide_lints/lib/field_guide_lints.dart`
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart`
- Create: `fg_lint_packages/field_guide_lints/lib/data_safety/data_safety_rules.dart`
- Create: `fg_lint_packages/field_guide_lints/lib/sync_integrity/sync_integrity_rules.dart`
- Create: `fg_lint_packages/field_guide_lints/lib/test_quality/test_quality_rules.dart`

**Agent**: `general-purpose`

#### Step 3.1.1: Create directory structure

Create the following directory tree:

```
fg_lint_packages/
  field_guide_lints/
    lib/
      architecture/
        rules/
      data_safety/
        rules/
      sync_integrity/
        rules/
      test_quality/
        rules/
    test/
```

#### Step 3.1.2: Create pubspec.yaml

Create `fg_lint_packages/field_guide_lints/pubspec.yaml`:

```yaml
name: field_guide_lints
description: Custom lint rules for the Field Guide construction inspector app.
version: 1.0.0
publish_to: none

environment:
  sdk: ^3.10.7

dependencies:
  # WHY: custom_lint_builder provides the DartLintRule base class and plugin registration.
  custom_lint_builder: ^0.7.0
  analyzer: ^7.0.0
  # NOTE: analyzer_plugin is a transitive dep of custom_lint_builder; pin to avoid version conflicts.
  analyzer_plugin: ^0.11.0

dev_dependencies:
  test: ^1.25.0
```

<!-- FROM SPEC: Section 2 - "fg_lint_packages/field_guide_lints/pubspec.yaml" -->
<!-- NOTE: SDK constraint matches app's sdk: ^3.10.7 for compatibility -->

#### Step 3.1.3: Create analysis_options.yaml

Create `fg_lint_packages/field_guide_lints/analysis_options.yaml`:

```yaml
include: package:lints/recommended.yaml

linter:
  rules:
    avoid_print: true
    annotate_overrides: true
```

#### Step 3.1.4: Create plugin entry file

Create `fg_lint_packages/field_guide_lints/lib/field_guide_lints.dart`:

```dart
/// Field Guide custom lint rules.
///
/// This package provides 46 lint rules organized in 4 categories:
/// - Architecture (17 rules): DI, layering, color system, file size, imports
/// - Data Safety (12 rules): Soft-delete, mounted checks, nullable guards, schema
/// - Sync Integrity (9 rules): ConflictAlgorithm, change_log, sync_control, RLS
/// - Test Quality (8 rules): TestingKeys, hardcoded delays, skip annotations
library field_guide_lints;

import 'package:custom_lint_builder/custom_lint_builder.dart';
import 'architecture/architecture_rules.dart';
import 'data_safety/data_safety_rules.dart';
import 'sync_integrity/sync_integrity_rules.dart';
import 'test_quality/test_quality_rules.dart';

/// Plugin entry point. Registers all lint rules with custom_lint.
PluginBase createPlugin() => _FieldGuideLintPlugin();

class _FieldGuideLintPlugin extends PluginBase {
  @override
  List<LintRule> getLintRules(CustomLintConfigs configs) => [
        // Architecture rules (A1-A17)
        ...architectureRules,
        // Data Safety rules (D1-D12)
        ...dataSafetyRules,
        // Sync Integrity rules (S1-S9)
        ...syncIntegrityRules,
        // Test Quality rules (T1-T8)
        ...testQualityRules,
      ];
}
```

#### Step 3.1.5: Create barrel exports

Create `fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart`:

```dart
import 'package:custom_lint_builder/custom_lint_builder.dart';

// Import all architecture rules here as they are created
// import 'rules/avoid_supabase_singleton.dart';
// ... (populated in sub-phase 3.2)

/// All architecture lint rules (A1-A17).
final List<LintRule> architectureRules = [
  // Populated in sub-phase 3.2
];
```

Create `fg_lint_packages/field_guide_lints/lib/data_safety/data_safety_rules.dart`:

```dart
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// All data safety lint rules (D1-D12).
final List<LintRule> dataSafetyRules = [
  // Populated in sub-phase 3.3
];
```

Create `fg_lint_packages/field_guide_lints/lib/sync_integrity/sync_integrity_rules.dart`:

```dart
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// All sync integrity lint rules (S1-S9).
final List<LintRule> syncIntegrityRules = [
  // Populated in sub-phase 3.4
];
```

Create `fg_lint_packages/field_guide_lints/lib/test_quality/test_quality_rules.dart`:

```dart
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// All test quality lint rules (T1-T8).
final List<LintRule> testQualityRules = [
  // Populated in sub-phase 3.5
];
```

#### Step 3.1.6: Verify package resolves

```
cd fg_lint_packages/field_guide_lints
```
Run: `pwsh -Command "cd fg_lint_packages/field_guide_lints; dart pub get"`
Expected: Dependencies resolve successfully.

---

### Sub-phase 3.2: Architecture Rules (A1-A17)

**Files:**
- Create: 17 rule files in `fg_lint_packages/field_guide_lints/lib/architecture/rules/`
- Modify: `fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/` test files

**Agent**: `general-purpose`

#### Step 3.2.1: Full exemplar implementation -- A1: avoid_supabase_singleton

Create `fg_lint_packages/field_guide_lints/lib/architecture/rules/avoid_supabase_singleton.dart`:

```dart
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A1: Flags `Supabase.instance.client` usage outside the DI root.
///
/// FROM SPEC: Section 5, A1 - "no Supabase.instance.client anywhere outside DI root"
/// Severity: ERROR
/// Allowed file: lib/core/di/app_initializer.dart (DI root)
/// Allowed file: lib/features/sync/application/background_sync_handler.dart (WorkManager isolate)
class AvoidSupabaseSingleton extends DartLintRule {
  AvoidSupabaseSingleton() : super(code: _code);

  static const _code = LintCode(
    name: 'avoid_supabase_singleton',
    problemMessage:
        'Avoid using Supabase.instance.client directly. '
        'Inject SupabaseClient via constructor from the DI root.',
    correctionMessage:
        'Accept SupabaseClient as a constructor parameter and '
        'wire it through AppInitializer/AppProviders.',
    errorSeverity: ErrorSeverity.ERROR,
  );

  /// Files where Supabase.instance.client is allowed.
  static const _allowedPaths = [
    'lib/core/di/app_initializer.dart',
    'lib/features/sync/application/background_sync_handler.dart',
  ];

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    // WHY: Check if this file is in the allowed list. If so, skip entirely.
    final filePath = resolver.path;
    for (final allowed in _allowedPaths) {
      if (filePath.endsWith(allowed)) return;
    }

    context.registry.addPropertyAccess((node) {
      // Looking for: Supabase.instance.client
      // AST structure: PropertyAccess(target: PrefixedIdentifier(Supabase.instance), propertyName: client)
      // OR: PropertyAccess(target: PropertyAccess(target: SimpleIdentifier(Supabase), propertyName: instance), propertyName: client)
      if (node.propertyName.name != 'client') return;

      final target = node.target;
      if (target is PrefixedIdentifier) {
        if (target.prefix.name == 'Supabase' &&
            target.identifier.name == 'instance') {
          reporter.atNode(node, _code);
        }
      } else if (target is PropertyAccess) {
        final innerTarget = target.target;
        if (innerTarget is SimpleIdentifier &&
            innerTarget.name == 'Supabase' &&
            target.propertyName.name == 'instance') {
          reporter.atNode(node, _code);
        }
      }
    });
  }
}
```

Create test: `fg_lint_packages/field_guide_lints/test/architecture/avoid_supabase_singleton_test.dart`:

```dart
// NOTE: custom_lint rules are tested by running dart run custom_lint against
// fixture files. For unit testing the rule logic itself, we verify the rule
// can be instantiated and has the correct code name.
import 'package:test/test.dart';
import 'package:field_guide_lints/architecture/rules/avoid_supabase_singleton.dart';

void main() {
  test('AvoidSupabaseSingleton has correct code name', () {
    final rule = AvoidSupabaseSingleton();
    expect(rule.code.name, 'avoid_supabase_singleton');
  });

  test('AvoidSupabaseSingleton has ERROR severity', () {
    final rule = AvoidSupabaseSingleton();
    expect(rule.code.errorSeverity.name, 'ERROR');
  });
}
```

#### Step 3.2.2: Remaining architecture rules (A2-A17) -- detection specifications

Each rule follows the same `DartLintRule` pattern as A1. The implementing agent must create one file per rule in `fg_lint_packages/field_guide_lints/lib/architecture/rules/`. Below is the detection specification for each:

| Rule | File Name | AST Node | Detection Logic | Severity | Allowlist |
|------|-----------|----------|----------------|----------|-----------|
| **A2** `no_direct_database_construction` | `no_direct_database_construction.dart` | `InstanceCreationExpression` | Match constructor call where type is `DatabaseService` and no arguments. Allowlist DI root. | ERROR | `app_initializer.dart`, `background_sync_handler.dart` |
| **A3** `no_raw_sql_in_presentation` | `no_raw_sql_in_presentation.dart` | `MethodInvocation` | Match `.query(`, `.rawQuery(`, `.rawInsert(`, `.rawUpdate(`, `.rawDelete(` calls. Only flag if file path contains `/presentation/`. | ERROR | None |
| **A4** `no_raw_sql_in_di` | `no_raw_sql_in_di.dart` | `MethodInvocation` | Same method names as A3. Only flag if file path contains `/di/`. | ERROR | None |
| **A5** `no_datasource_import_in_presentation` | `no_datasource_import_in_presentation.dart` | `ImportDirective` | Match imports containing `datasource` or `datasources` in URI. Only flag if file path contains `/presentation/`. | ERROR | None |
| **A6** `no_business_logic_in_di` | `no_business_logic_in_di.dart` | `AwaitExpression`, `TryStatement` | Flag `await`, `try`/`catch`, `.transaction(` calls in files whose path contains `/di/`. | WARNING | None |
| **A7** `single_composition_root` | `single_composition_root.dart` | `InstanceCreationExpression` | Match `Provider(`, `ChangeNotifierProvider(`, `ProxyProvider(` constructors. Only flag if file is NOT `app_providers.dart` and NOT a `*_providers.dart` file in a `/di/` directory. | WARNING | `app_providers.dart`, `*/di/*_providers.dart` |
| **A8** `no_service_construction_in_widgets` | `no_service_construction_in_widgets.dart` | `InstanceCreationExpression` | Match constructors of known service classes (`PermissionService`, `ImageService`, `PhotoService`). Only flag in `/presentation/` files. | WARNING | None |
| **A9** `no_silent_catch` | `no_silent_catch.dart` | `CatchClause` | Visit catch clause body. If body contains no `MethodInvocation` where method name starts with `Logger.`, flag it. | WARNING | `logger.dart` (allow Logger's own catches) |
| **A10** `max_file_length` | `max_file_length.dart` | `CompilationUnit` | Count lines via `resolver.source.contents.data.split('\n').length`. Warn >500, error >1000. | WARN/ERR | None |
| **A11** `max_import_count` | `max_import_count.dart` | `CompilationUnit` | Count `ImportDirective` nodes. Warn >25, error >40. | WARN/ERR | None |
| **A12** `no_deprecated_app_theme` | `no_deprecated_app_theme.dart` | `PrefixedIdentifier` / `PropertyAccess` | Match `AppTheme.*` where the member is a deprecated color constant (not `darkTheme`, `lightTheme`, `highContrastTheme`, `getPrimaryGradient`, `getGlassmorphicDecoration`). | ERROR | None |
| **A13** `no_hardcoded_colors` | `no_hardcoded_colors.dart` | `PrefixedIdentifier` | Match `Colors.*` in `/presentation/` files. Allowlist `Colors.transparent`. | WARNING | None for transparent |
| **A14** `no_hardcoded_form_type` | `no_hardcoded_form_type.dart` | `SimpleStringLiteral` | Match string literals containing `mdot_0582b`. Only flag if file is NOT `builtin_forms.dart`. | WARNING | `builtin_forms.dart` |
| **A15** `no_duplicate_service_instances` | `no_duplicate_service_instances.dart` | `InstanceCreationExpression` | Track service class constructor calls across the file. If same class is constructed 2+ times, flag second occurrence. Only in `/di/` files. | WARNING | None |
| **A16** `annotate_overrides` | N/A -- use built-in `annotate_overrides` rule from lints package | N/A | Already enabled in `analysis_options.yaml`. No custom implementation needed. | WARNING | N/A |
| **A17** `no_async_lifecycle_without_await` | `no_async_lifecycle_without_await.dart` | `MethodDeclaration` | Match methods named `initState`, `dispose`, `didChangeDependencies`, `didUpdateWidget` with `async` keyword. Check if any `AwaitExpression` exists in body. If async but no await, flag. | WARNING | None |

<!-- NOTE: A16 is a built-in rule, not a custom lint. Skip creating a file for it. The barrel export should contain only 16 custom rules. -->

#### Step 3.2.3: Update barrel export

Update `fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart` to import all 16 custom rule files and populate the `architectureRules` list:

```dart
import 'package:custom_lint_builder/custom_lint_builder.dart';
import 'rules/avoid_supabase_singleton.dart';
import 'rules/no_direct_database_construction.dart';
import 'rules/no_raw_sql_in_presentation.dart';
import 'rules/no_raw_sql_in_di.dart';
import 'rules/no_datasource_import_in_presentation.dart';
import 'rules/no_business_logic_in_di.dart';
import 'rules/single_composition_root.dart';
import 'rules/no_service_construction_in_widgets.dart';
import 'rules/no_silent_catch.dart';
import 'rules/max_file_length.dart';
import 'rules/max_import_count.dart';
import 'rules/no_deprecated_app_theme.dart';
import 'rules/no_hardcoded_colors.dart';
import 'rules/no_hardcoded_form_type.dart';
import 'rules/no_duplicate_service_instances.dart';
import 'rules/no_async_lifecycle_without_await.dart';

/// All architecture lint rules (A1-A15, A17). A16 is a built-in lint.
final List<LintRule> architectureRules = [
  AvoidSupabaseSingleton(),
  NoDirectDatabaseConstruction(),
  NoRawSqlInPresentation(),
  NoRawSqlInDi(),
  NoDatasourceImportInPresentation(),
  NoBusinessLogicInDi(),
  SingleCompositionRoot(),
  NoServiceConstructionInWidgets(),
  NoSilentCatch(),
  MaxFileLength(),
  MaxImportCount(),
  NoDeprecatedAppTheme(),
  NoHardcodedColors(),
  NoHardcodedFormType(),
  NoDuplicateServiceInstances(),
  NoAsyncLifecycleWithoutAwait(),
];
```

#### Step 3.2.4: Create basic tests for each rule

For each rule, create a test file in `fg_lint_packages/field_guide_lints/test/architecture/` that verifies:
1. The rule can be instantiated
2. The code name matches the expected name
3. The severity matches the expected level

Follow the pattern from Step 3.2.1's test.

#### Step 3.2.5: Verify

Run: `pwsh -Command "cd fg_lint_packages/field_guide_lints; dart pub get; dart test"`
Expected: All rule instantiation tests pass.

---

### Sub-phase 3.3: Data Safety Rules (D1-D12)

**Files:**
- Create: 12 rule files in `fg_lint_packages/field_guide_lints/lib/data_safety/rules/`
- Modify: `fg_lint_packages/field_guide_lints/lib/data_safety/data_safety_rules.dart`
- Create: `fg_lint_packages/field_guide_lints/test/data_safety/` test files

**Agent**: `general-purpose`

#### Step 3.3.1: Data safety rules -- detection specifications

| Rule | File Name | AST Node | Detection Logic | Severity | Allowlist |
|------|-----------|----------|----------------|----------|-----------|
| **D1** `avoid_raw_database_delete` | `avoid_raw_database_delete.dart` | `MethodInvocation` | Match `.delete(` on a `Database` receiver. Flag if file path does NOT contain `soft_delete_service`, `generic_local_datasource`, or `sync/engine/`. | ERROR | `soft_delete_service.dart`, `generic_local_datasource.dart`, `sync/engine/*` |
| **D2** `require_soft_delete_filter` | `require_soft_delete_filter.dart` | `MethodInvocation` | Match `.query(` on a `Database` receiver. Check if `where` argument contains `deleted_at IS NULL` (string check on argument expression). Flag if missing and file is NOT inside `generic_local_datasource.dart` (which has `_whereWithDeletedFilter`). | ERROR | `generic_local_datasource.dart`, `sync/engine/*` |
| **D3** `avoid_unguarded_firstwhere` | `avoid_unguarded_firstwhere.dart` | `MethodInvocation` | Match `.firstWhere(` calls. Check if named argument `orElse:` is present. If not, flag. | ERROR | None |
| **D4** `tomap_field_completeness` | `tomap_field_completeness.dart` | `MethodDeclaration` | Match method named `toMap` that returns `Map<String, dynamic>`. This is a WARNING-level informational check -- the full cross-file validation (constructor params vs toMap keys) is a CI script (spec Section 9, D9). For the lint rule, check that `toMap` body contains map literal entries and flag if obviously empty. | WARNING | None |
| **D5** `require_mounted_check_after_async` | `require_mounted_check_after_async.dart` | `AwaitExpression` | In a method body, find `await` expressions. After each await, check if `context` (as `BuildContext` type) is accessed before a `mounted` check. Complex -- may need to walk statements sequentially. | ERROR | Non-`StatefulWidget` classes |
| **D6** `copywith_nullable_sentinel` | `copywith_nullable_sentinel.dart` | `MethodDeclaration` | Match method named `copyWith`. Check if any parameter that is nullable uses `??` in the body. If yes, flag -- should use sentinel pattern (`Object? x = _sentinel`). | WARNING | None |
| **D7** `check_bytes_null_and_empty` | `check_bytes_null_and_empty.dart` | `IfStatement` | Match null checks on `Uint8List` typed variables. Check if `.isEmpty` is also checked. Flag if only null check without `.isEmpty`. | WARNING | None |
| **D8** `no_sentinel_strings_in_data` | `no_sentinel_strings_in_data.dart` | `SimpleStringLiteral` | Match string literal `'--'` in files under `/data/` or `/models/`. | WARNING | None |
| **D9** `schema_column_consistency` | N/A -- CI script only | N/A | Cross-file analysis (fromMap keys vs DDL columns). Cannot be implemented as a single-file lint rule. Implement as a CI script in Phase 4. | ERROR | N/A |
| **D10** `migration_column_before_index` | `migration_column_before_index.dart` | `SimpleStringLiteral` | Match SQL strings containing `CREATE INDEX`. Check if the referenced column's `ALTER TABLE ADD COLUMN` appears earlier in the same string or file. Grep-based in practice. | ERROR | None |
| **D11** `migration_requires_if_exists` | `migration_requires_if_exists.dart` | `SimpleStringLiteral` | Match SQL strings containing `ALTER TABLE`. Flag if string does not contain `IF EXISTS`. | WARNING | None |
| **D12** `path_traversal_guard` | `path_traversal_guard.dart` | `MethodInvocation` | Match `.contains('..')` on path-like variables. Flag as insufficient guard -- should use `path.normalize()` and check against base directory. | ERROR | None |

<!-- NOTE: D9 is a CI-only check (cross-file). D4 is simplified for lint (full check is CI). D10 and D11 operate on SQL string literals. -->

#### Step 3.3.2: Implement all 11 custom rules (D9 is CI-only)

Follow the same pattern as the A1 exemplar for each rule. Each file should:
1. Extend `DartLintRule`
2. Define a `LintCode` with the correct name, message, and severity
3. Override `run()` with the detection logic
4. Include allowlist path checks where applicable

#### Step 3.3.3: Update barrel export

Update `data_safety_rules.dart` to import all 11 rule files and populate the list.

#### Step 3.3.4: Create basic tests

Same pattern as Step 3.2.4.

#### Step 3.3.5: Verify

Run: `pwsh -Command "cd fg_lint_packages/field_guide_lints; dart test"`
Expected: All rule instantiation tests pass.

---

### Sub-phase 3.4: Sync Integrity Rules (S1-S9)

**Files:**
- Create: 9 rule files in `fg_lint_packages/field_guide_lints/lib/sync_integrity/rules/`
- Modify: `fg_lint_packages/field_guide_lints/lib/sync_integrity/sync_integrity_rules.dart`
- Create: `fg_lint_packages/field_guide_lints/test/sync_integrity/` test files

**Agent**: `general-purpose`

#### Step 3.4.1: Sync integrity rules -- detection specifications

| Rule | File Name | AST Node | Detection Logic | Severity | Allowlist |
|------|-----------|----------|----------------|----------|-----------|
| **S1** `conflict_algorithm_ignore_guard` | `conflict_algorithm_ignore_guard.dart` | `MethodInvocation` | Match `.insert(` with named argument `conflictAlgorithm: ConflictAlgorithm.ignore`. Check if the return value is captured (`VariableDeclarationStatement` or assignment). If not captured, or if no subsequent `if (rowId == 0)` / `if (result == 0)` check within 5 statements, flag. | ERROR | `sync_engine.dart` (already has correct pattern) |
| **S2** `change_log_cleanup_requires_success` | `change_log_cleanup_requires_success.dart` | `MethodInvocation` | Match `.delete(` with string argument `'change_log'`. Check if the delete is inside an `if` block that checks for success condition. If unconditional, flag. | ERROR | None |
| **S3** `sync_control_inside_transaction` | `sync_control_inside_transaction.dart` | `MethodInvocation` | Match `.execute(` or `.rawUpdate(` with string containing `sync_control`. Check if the call is inside a `try`/`finally` block. If not, flag. | ERROR | None |
| **S4** `no_sync_status_column` | `no_sync_status_column.dart` | `SimpleStringLiteral` | Match string literals containing `sync_status` in schema files, model files, or migration code. | ERROR | None |
| **S5** `tomap_includes_project_id` | `tomap_includes_project_id.dart` | `MethodDeclaration` | Match `toMap()` methods in files under `/data/models/`. Check if the map literal contains a `'project_id'` key. Flag if missing and the class name suggests it is a project-scoped entity (heuristic: file is in a feature that has project_id in its table schema). | ERROR | Models that are not project-scoped |
| **S6** `no_state_reload_after_rpc` | `no_state_reload_after_rpc.dart` | `MethodInvocation` | Match `.rpc(` calls (Supabase RPC). Check if a state refresh / data reload call follows within the same method. Heuristic: look for `notifyListeners()`, `loadData()`, `.refresh()` after the RPC call. | WARNING | None |
| **S7** `cached_connectivity_recheck` | `cached_connectivity_recheck.dart` | `PrefixedIdentifier` / `SimpleIdentifier` | Match access to `_isOnline` field. Check if the access is preceded by a connectivity recheck within the same method (heuristic: look for `checkConnectivity()` or similar). | WARNING | None |
| **S8** `sync_time_on_success_only` | `sync_time_on_success_only.dart` | `AssignmentExpression` | Match assignments to `_lastSyncTime` or `lastSyncTime`. Check if the assignment is inside a success condition (try block before catch, or inside an `if (result.errors == 0)` check). | WARNING | None |
| **S9** `rls_column_must_exist` | N/A -- SQL CI script | N/A | Cross-file SQL analysis. Implement as CI script in Phase 4. | ERROR | N/A |

<!-- NOTE: S9 is a CI-only check. S5 requires heuristic detection. S6 and S7 are pattern-based heuristics. -->

#### Step 3.4.2: Implement all 8 custom rules (S9 is CI-only)

Follow the DartLintRule pattern. For heuristic rules (S5, S6, S7), err on the side of fewer false positives -- only flag clear violations.

#### Step 3.4.3: Update barrel export

Update `sync_integrity_rules.dart` to import all 8 rule files.

#### Step 3.4.4: Create basic tests

Same pattern as Step 3.2.4.

#### Step 3.4.5: Verify

Run: `pwsh -Command "cd fg_lint_packages/field_guide_lints; dart test"`
Expected: All rule instantiation tests pass.

---

### Sub-phase 3.5: Test Quality Rules (T1-T8)

**Files:**
- Create: 8 rule files in `fg_lint_packages/field_guide_lints/lib/test_quality/rules/`
- Modify: `fg_lint_packages/field_guide_lints/lib/test_quality/test_quality_rules.dart`
- Create: `fg_lint_packages/field_guide_lints/test/test_quality/` test files

**Agent**: `general-purpose`

#### Step 3.5.1: Test quality rules -- detection specifications

| Rule | File Name | AST Node | Detection Logic | Severity | Allowlist |
|------|-----------|----------|----------------|----------|-----------|
| **T1** `no_hardcoded_key_in_widgets` | `no_hardcoded_key_in_widgets.dart` | `InstanceCreationExpression` | Match `Key('...')` constructor calls in `lib/` files (not `test/`). Also match `ValueKey('...')` with string literal argument. | WARNING | `testing_keys.dart` and its sub-key files |
| **T2** `no_hardcoded_key_in_tests` | `no_hardcoded_key_in_tests.dart` | `InstanceCreationExpression` | Match `Key('...')` and `ValueKey('...')` in `test/` files. | WARNING | None |
| **T3** `no_hardcoded_delays_in_tests` | `no_hardcoded_delays_in_tests.dart` | `MethodInvocation` | Match `Future.delayed(` in `test/` files. | WARNING | None |
| **T4** `no_skip_without_issue_ref` | `no_skip_without_issue_ref.dart` | `NamedExpression` | Match `skip:` named argument in `test()` or `group()` calls. Check if the skip value string contains a bug/issue reference (regex: `BUG-`, `#\d+`, `BLOCKER-`, `TODO-`). If not, flag. | INFO | None |
| **T5** `no_ignore_for_file_in_tests` | `no_ignore_for_file_in_tests.dart` | Comment scan | Match `// ignore_for_file:` comments in `test/` files. Use `CompilationUnit` to check source text for the pattern. | WARNING | None |
| **T6** `no_stale_patrol_references` | `no_stale_patrol_references.dart` | `ImportDirective` | Match imports containing `patrol` or `flutter_driver` package URIs. | WARNING | None |
| **T7** `no_direct_testing_keys_bypass` | `no_direct_testing_keys_bypass.dart` | `ImportDirective` | Match imports containing `testing_keys/keys/` (sub-key files) in `lib/` files. Should import `testing_keys/testing_keys.dart` facade instead. | WARNING | Files inside `testing_keys/` directory itself |
| **T8** `require_did_update_widget_for_controllers` | `require_did_update_widget_for_controllers.dart` | `ClassDeclaration` | Match classes extending `State<*>`. Check if class has a field typed as `*Controller` (TextEditingController, ScrollController, etc.). If yes, check if `didUpdateWidget` method exists. If not, flag. | ERROR | None |

#### Step 3.5.2: Implement all 8 rules

Follow the DartLintRule pattern.

#### Step 3.5.3: Update barrel export

Update `test_quality_rules.dart` to import all 8 rule files.

#### Step 3.5.4: Create basic tests

Same pattern as Step 3.2.4.

#### Step 3.5.5: Verify

Run: `pwsh -Command "cd fg_lint_packages/field_guide_lints; dart test"`
Expected: All rule instantiation tests pass.

---

### Sub-phase 3.6: Integration -- Wire Lint Package into App

**Files:**
- Modify: `pubspec.yaml` (add dev_dependencies)
- Modify: `analysis_options.yaml` (add custom_lint plugin)

**Agent**: `general-purpose`

#### Step 3.6.1: Add custom_lint and lint package to app pubspec.yaml

Add to the `dev_dependencies:` section of `pubspec.yaml`:

```yaml
dev_dependencies:
  # ... existing deps ...

  # FROM SPEC: Section 13 Phase 3 - "Add custom_lint and custom_lint_builder to dev_dependencies"
  custom_lint: ^0.7.0

  # Path dependency to local lint package
  field_guide_lints:
    path: fg_lint_packages/field_guide_lints
```

<!-- NOTE: The app only needs `custom_lint` (not `custom_lint_builder`). The builder is a dependency of the lint package itself. -->

#### Step 3.6.2: Add custom_lint plugin to analysis_options.yaml

Add to `analysis_options.yaml`:

```yaml
analyzer:
  plugins:
    - custom_lint
  errors:
    # ... existing error overrides ...
```

The full `analysis_options.yaml` should now look like:

```yaml
include: package:lints/recommended.yaml

analyzer:
  plugins:
    - custom_lint
  errors:
    deprecated_member_use_from_same_package: error
    use_build_context_synchronously: error
    unused_import: error
  exclude:
    - "**/*.g.dart"
    - "**/*.freezed.dart"
    - "**/*.mocks.dart"
    - "packages/**"
    - "build/**"
    - "fg_lint_packages/**"

linter:
  rules:
    avoid_print: true
    annotate_overrides: true
    unnecessary_overrides: true
    prefer_single_quotes: true
    prefer_const_constructors: true
    prefer_const_declarations: true
    prefer_final_locals: true
    avoid_unnecessary_containers: true
    sized_box_for_whitespace: true
    use_key_in_widget_constructors: true
    no_duplicate_case_values: true
    avoid_types_as_parameter_names: true
    empty_catches: true
    null_closures: true
    prefer_is_empty: true
    prefer_is_not_empty: true
    unnecessary_new: true
    unnecessary_this: true
    prefer_collection_literals: true
```

<!-- NOTE: Added `fg_lint_packages/**` to exclude list so the analyzer doesn't analyze the lint package as part of the app. -->

#### Step 3.6.3: Resolve dependencies

Run: `pwsh -Command "flutter pub get"`
Expected: All dependencies resolve including the path dependency to `field_guide_lints`.

#### Step 3.6.4: Run custom_lint to verify zero violations

Run: `pwsh -Command "dart run custom_lint"`
Expected: Zero violations. Phase 2 cleaned up all existing violations, so the lint rules should find nothing.

If any violations are found, they indicate either:
1. A Phase 2 cleanup was incomplete (go back and fix)
2. A lint rule has false positives (adjust the rule's detection logic or allowlist)

#### Step 3.6.5: Run full analyze

Run: `pwsh -Command "flutter analyze"`
Expected: `No issues found!`

#### Step 3.6.6: Run full test suite

Run: `pwsh -Command "flutter test"`
Expected: All tests pass. The lint package addition should not affect runtime behavior.

#### Step 3.6.7: Verify VS Code squiggles (manual check)

Open VS Code with the project. Open a file that previously had a violation (e.g., any file in `lib/features/*/presentation/`). Temporarily add a violation:

```dart
// Temporary test -- add and then remove:
final color = AppTheme.primaryCyan;  // Should show red squiggle from A12
```

If the squiggle appears, custom_lint integration is working. Remove the test line.

<!-- FROM SPEC: Success criteria - "All 4 lint packages show real-time VS Code squiggles" -->
