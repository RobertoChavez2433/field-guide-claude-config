# Automated Quality Gates Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Deploy a 3-layer quality gate system (pre-commit + CI + branch protection) with 46 custom lint rules across 4 packages, enforcing architectural patterns discovered in 700+ development sessions.
**Spec:** `.claude/specs/2026-03-31-automated-quality-gates-spec.md`
**Tailor:** `.claude/tailor/2026-03-31-automated-quality-gates/`

**Architecture:** Clean-slate approach: fix all existing violations first (Phase 2), then enable custom lint rules (Phase 3), then deploy hooks and CI (Phases 4-5), finally configure branch protection (Phase 6). This ensures lint rules start at zero violations and every new violation is immediately blocked.
**Tech Stack:** Dart `custom_lint` + `custom_lint_builder` (Remi Rousselet), GitHub Actions, PowerShell pre-commit hooks, `gh` CLI for branch protection.
**Blast Radius:** 76+ files (AppTheme migration), 6 files (Supabase DI), 3 files (DatabaseService DI), 46 new lint rule files, 4 CI workflows, 5 hook scripts, 5 rule doc updates.

---

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

#### Step 1.1.5: Remove patrol and flutter_driver dev dependencies

Open `pubspec.yaml` and remove `patrol: ^4.1.0` from `dev_dependencies`. Also remove the `patrol:` configuration block (app name, Android/iOS config) from `pubspec.yaml`. Remove `flutter_driver` from `dev_dependencies` if present.

Run: `pwsh -Command "flutter pub get"`
Expected: Resolves successfully without patrol or flutter_driver.

<!-- WHY: Patrol and flutter_driver are deprecated testing stacks. Lint rule T6 will block their imports, but the dependency itself must also be removed to prevent accidental usage. -->

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
    # TODO: Upgrade to error after Phase 2.1 AppTheme migration
    deprecated_member_use_from_same_package: warning
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
    # FROM SPEC: Section 13 Phase 1 — "Enable: ... unused_field"
    unused_field: true
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

Since `deprecated_member_use_from_same_package` was set to WARNING in Step 1.2.1, AppTheme consumer usages will appear as warnings, not errors. This is expected -- Phase 2.1 will migrate them all, then Step 2.1.6 upgrades the severity to ERROR.

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
| `statusSuccess` / `success` | `FieldGuideColors.of(context).statusSuccess` | 2 |
| `statusWarning` / `warning` | `FieldGuideColors.of(context).statusWarning` | 2 |
| `statusError` / `error` | `Theme.of(context).colorScheme.error` | 1 |
| `statusInfo` | `FieldGuideColors.of(context).statusInfo` | 2 |
| `surfaceElevated` | `Theme.of(context).colorScheme.surfaceContainerHigh` | 1 |
| `surfaceHighlight` | `Theme.of(context).colorScheme.outlineVariant` | 1 |
| `surfaceBright` / `surfaceHighest` | `Theme.of(context).colorScheme.surfaceContainerHighest` | 1 |
| `textPrimary` | `Theme.of(context).colorScheme.onSurface` | 1 |
| `textSecondary` | `Theme.of(context).colorScheme.onSurfaceVariant` | 1 |
| `textTertiary` | `FieldGuideColors.of(context).textTertiary` | 2 |
| `textInverse` | `FieldGuideColors.of(context).textInverse` | 2 |

<!-- NOTE: The @Deprecated annotations in app_theme.dart specify replacements. However, some annotations have INCORRECT replacement targets (e.g., `warning` points to `.warning` but the correct FieldGuideColors member is `.statusWarning`). Always use this migration map, not the annotation text. -->

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

**Exemplar file**: `lib/features/calculator/presentation/screens/calculator_screen.dart` (26 color refs)

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

**Exemplar file**: `lib/features/auth/presentation/screens/company_setup_screen.dart` (17 color refs)

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
abstract class BaseRemoteDatasource<T> {
  SupabaseClient get supabase => Supabase.instance.client;
}

// AFTER:
abstract class BaseRemoteDatasource<T> {
  final SupabaseClient supabase;
  // WHY: Constructor injection replaces singleton access. Client is resolved once in DI root.
  BaseRemoteDatasource(this.supabase);
}
```

Then audit all 16 concrete subclasses of `BaseRemoteDatasource` to pass through the `SupabaseClient` parameter. Each subclass constructor must call `super(supabaseClient)`. The `SupabaseClient` is already available in the DI tree via `app_initializer.dart` which passes it when constructing datasources.

#### Step 2.2.3: Add supabaseClient getter to AppDependencies

Add a `SupabaseClient? get supabaseClient` getter to `AppDependencies` in `lib/core/di/app_initializer.dart` that returns the client from `CoreDeps`. This is a prerequisite for Steps 2.2.4-2.2.6 which reference `deps.supabaseClient`.

<!-- WHY: Multiple provider files need the SupabaseClient from the DI root. Exposing it via AppDependencies avoids Supabase.instance.client calls in provider factories. -->

#### Step 2.2.4: Fix auth_providers.dart

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

<!-- NOTE: AppDependencies.supabaseClient getter was added in Step 2.2.3. -->

#### Step 2.2.5: Fix consent_support_factory.dart

At `lib/features/settings/di/consent_support_factory.dart:46`:

```dart
// Read the file to understand its signature, then inject SupabaseClient
// via the factory function parameter instead of Supabase.instance.client.
```

The implementing agent must read the full file, understand how the factory is called, and wire the `SupabaseClient` from the DI tree (through `settings_providers` or `app_providers`).

#### Step 2.2.6: Fix sync_providers.dart

At `lib/features/sync/di/sync_providers.dart:58`:

Similar to auth_providers -- add a `SupabaseClient?` parameter to `SyncProviders.providers()` and pass it from `buildAppProviders()`.

Also fix line 144 (`ConflictAlgorithm.ignore` in sync_providers -- this is a separate sub-phase 2.5 concern but the singleton is the 2.2 fix).

#### Step 2.2.7: Fix sync_orchestrator.dart

At `lib/features/sync/application/sync_orchestrator.dart:225,384`:

The `SyncOrchestrator` class should accept `SupabaseClient` via constructor injection (it likely already does for some code paths). Replace the two inline `Supabase.instance.client` usages with the injected field.

#### Step 2.2.8: Fix background_sync_handler.dart (special case)

At `lib/features/sync/application/background_sync_handler.dart:49,151`:

This is a **top-level function** (`backgroundSyncCallback`) running in a WorkManager isolate. It MUST call `Supabase.initialize()` and then access `Supabase.instance.client` because there is no DI tree in the isolate.

No `// ignore:` comments are needed here. The A1 lint rule's allowlist already includes `background_sync_handler.dart`, so the rule will skip this file entirely.

<!-- WHY: WorkManager isolate has no access to DI tree. This is the documented exception per spec Section 4 / A1 rule. The lint rule allowlist handles it — no inline suppression needed. -->

#### Step 2.2.9: Verify

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

This is in the WorkManager isolate callback. Similar to the Supabase case, DatabaseService must be constructed fresh in the isolate because there is no DI tree. No `// ignore:` comment is needed — the A2 lint rule's allowlist already includes `background_sync_handler.dart`, so the rule will skip this file entirely.

<!-- WHY: WorkManager isolate starts fresh -- no static state, no Provider tree. DatabaseService must be constructed inline. The lint rule allowlist handles it — no inline suppression needed. -->

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

### Sub-phase 2.11: Hardcoded Key('...') in Tests — T2 Cleanup

**Files:**
- Modify: Test files in `test/` containing hardcoded `Key('...')` or `ValueKey('...')`

**Agent**: `qa-testing-agent`

#### Step 2.11.1: Replace hardcoded keys in test files

Search for `Key('` and `ValueKey('` in `test/` files. Replace each with `TestingKeys.*` references, following the same pattern as Sub-phase 2.6.1 but for test code.

<!-- FROM SPEC: T2 rule — "use TestingKeys in test code" -->

---

### Sub-phase 2.12: ignore_for_file Cleanup in Tests — T5 Cleanup

**Files:**
- Modify: ~32 test files with `// ignore_for_file:` directives

**Agent**: `qa-testing-agent`

#### Step 2.12.1: Audit and fix ignore_for_file in test files

Search for `// ignore_for_file:` in `test/` files. For each occurrence:
1. If the underlying lint issue can be quickly fixed, fix it and remove the suppression
2. If the issue is structural (e.g., generated mock patterns), add a justification comment explaining why the suppression is needed
3. If fixing would require significant refactoring, leave the suppression but add a `// TODO:` with a brief rationale

**Alternative**: Configure T5 as INFO severity (not blocking) since these are test files. The implementing agent should decide based on the nature of the suppressions found.

<!-- FROM SPEC: T5 rule — "no lint suppressions in test/" — currently 32 suppressions -->

---

### Sub-phase 2.13: Skip Annotations Without Issue Refs — T4 Best-Effort

**Files:**
- Modify: ~12 test files with `skip:` arguments lacking issue references

**Agent**: `qa-testing-agent`

#### Step 2.13.1: Add issue refs to skipped tests (best-effort)

Search for `skip:` in `test/` files. For each skipped test that lacks a bug/issue reference (`BUG-`, `#\d+`, `BLOCKER-`), add the appropriate reference if known, or add `// TODO: add issue ref` if the reason is unclear.

**NOTE**: T4 is INFO severity per spec, so it will not block commits or CI. This is a best-effort improvement for the 12 existing skips.

<!-- FROM SPEC: T4 rule — INFO severity, "skip: must reference a bug/issue" -->

---

### Sub-phase 2.14: Final Clean Slate Verification

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 2.14.1: Full analyze

Run: `pwsh -Command "flutter analyze"`
Expected: `No issues found!`

#### Step 2.14.2: Full test suite

Run: `pwsh -Command "flutter test"`
Expected: All tests pass.

#### Step 2.14.3: Verify deprecated_member_use_from_same_package is error

Confirm `analysis_options.yaml` has:
```yaml
deprecated_member_use_from_same_package: error
```

And analyze still passes (meaning zero deprecated member usages remain).

#### Step 2.14.4: Verify D2 soft-delete filter violations are zero

After the D2 lint rule is enabled (Phase 3.3), the allowlist covers `generic_local_datasource.dart` and `sync/engine/*`. The implementing agent must verify that D2 produces zero violations after allowlisting. If any violations exist, audit and fix them before proceeding to Phase 3.6.

<!-- FROM SPEC: D2 rule — "require_soft_delete_filter" — allowlists generic_local_datasource and sync/engine -->

#### Step 2.14.5: Verify D4 toMap completeness violations are zero

After the D4 lint rule is enabled (Phase 3.3), verify zero violations from the simplified lint check (flags obviously empty `toMap()` methods). If any exist, fix them. The full cross-file check (D9) runs in CI only.

<!-- FROM SPEC: D4 rule — WARNING, simplified lint; D9 rule — CI-only cross-file check -->

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
  # analyzer resolved transitively via custom_lint_builder — do NOT pin explicitly

dev_dependencies:
  test: ^1.25.0
  lints: ^5.1.1  # Required for analysis_options.yaml include
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
import 'package:analyzer/error/error.dart' show ErrorSeverity;
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
    // NOTE: Use contains() with full relative path segments to avoid suffix
    // spoofing (e.g., a file named "fake_app_initializer.dart" would not match).
    final filePath = resolver.path;
    for (final allowed in _allowedPaths) {
      if (filePath.contains(allowed)) return;
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
| **A9** `no_silent_catch` | `no_silent_catch.dart` | `CatchClause` | Visit catch clause body. If body contains no `MethodInvocation` where the target is a `SimpleIdentifier` named `Logger`, flag it. | WARNING | `logger.dart` (allow Logger's own catches) |
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
| **D9** `schema_column_consistency` | N/A -- CI script only | N/A | Cross-file analysis (fromMap keys vs DDL columns). Cannot be implemented as a single-file lint rule. Implement as a CI script in Phase 5. | ERROR | N/A |
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
| **S9** `rls_column_must_exist` | N/A -- SQL CI script | N/A | Cross-file SQL analysis. Implement as CI script in Phase 5. | ERROR | N/A |

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
    unused_field: true
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

---

## Phase 4: Pre-Commit Hook System

### Sub-phase 4.1: Archive Existing Pre-Commit Hook

**Files:**
- Move: `.claude/hooks/pre-commit.ps1` → `.claude/hooks/archived/pre-commit-v1.ps1`

**Agent**: `general-purpose`

#### Step 4.1.1: Archive the current hook

```powershell
Copy-Item ".claude/hooks/pre-commit.ps1" ".claude/hooks/archived/pre-commit-v1.ps1"
```

<!-- WHY: Preserve the existing hook for reference. The archived/ directory already exists per ground truth. -->

---

### Sub-phase 4.2: Create Check Scripts

**Files:**
- Create: `.claude/hooks/checks/run-analyze.ps1`
- Create: `.claude/hooks/checks/run-custom-lint.ps1`
- Create: `.claude/hooks/checks/run-tests.ps1`
- Create: `.claude/hooks/checks/grep-checks.ps1`

**Agent**: `general-purpose`

#### Step 4.2.1: Create run-analyze.ps1

Create `.claude/hooks/checks/run-analyze.ps1`:

```powershell
# Run dart analyze — zero errors/warnings required
# FROM SPEC: Section 10 — "dart analyze (zero errors/warnings)"

param()

Write-Host "=== Running dart analyze ===" -ForegroundColor Cyan

$output = & flutter analyze 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "FAILED: dart analyze found issues:" -ForegroundColor Red
    $output | ForEach-Object { Write-Host $_ }
    exit 1
}

Write-Host "PASSED: dart analyze" -ForegroundColor Green
exit 0
```

#### Step 4.2.2: Create run-custom-lint.ps1

Create `.claude/hooks/checks/run-custom-lint.ps1`:

```powershell
# Run custom_lint — zero violations required
# FROM SPEC: Section 10 — "custom_lint check"

param()

Write-Host "=== Running custom_lint ===" -ForegroundColor Cyan

$output = & dart run custom_lint 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "FAILED: custom_lint found violations:" -ForegroundColor Red
    $output | ForEach-Object { Write-Host $_ }
    exit 1
}

# Also check output for lint warnings (custom_lint may exit 0 but print warnings)
$violations = $output | Where-Object { $_ -match '(WARNING|ERROR|INFO)\s*-' }
if ($violations.Count -gt 0) {
    Write-Host "FAILED: custom_lint found $($violations.Count) violation(s):" -ForegroundColor Red
    $violations | ForEach-Object { Write-Host $_ }
    exit 1
}

Write-Host "PASSED: custom_lint" -ForegroundColor Green
exit 0
```

#### Step 4.2.3: Create run-tests.ps1

Create `.claude/hooks/checks/run-tests.ps1`:

```powershell
# Run targeted flutter tests for changed files only
# FROM SPEC: Section 10 — "flutter test (targeted — changed files only)"
# Test targeting: lib/features/{feature}/.../file.dart → test/features/{feature}/.../file_test.dart

param()

Write-Host "=== Running targeted tests ===" -ForegroundColor Cyan

# Get staged .dart files (excluding generated)
$stagedFiles = @(git diff --cached --name-only --diff-filter=ACM | Where-Object {
    $_ -match '\.dart$' -and
    $_ -notmatch '\.(g|freezed|mocks)\.dart$'
})

if ($stagedFiles.Count -eq 0) {
    Write-Host "No staged Dart files — skipping tests." -ForegroundColor Yellow
    exit 0
}

# Map source files to test files
$testFiles = @()
foreach ($file in $stagedFiles) {
    if ($file -match '^lib/(.+)\.dart$') {
        $testPath = "test/$($Matches[1])_test.dart"
        if (Test-Path $testPath) {
            $testFiles += $testPath
        }
    }
}

$uniqueTests = $testFiles | Sort-Object -Unique

if ($uniqueTests.Count -eq 0) {
    Write-Host "No matching test files found — skipping. (CI runs full suite.)" -ForegroundColor Yellow
    exit 0
}

Write-Host "Running $($uniqueTests.Count) test file(s)..." -ForegroundColor Cyan

$failed = $false
foreach ($testFile in $uniqueTests) {
    Write-Host "  Testing: $testFile"
    & flutter test $testFile 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED: $testFile" -ForegroundColor Red
        $failed = $true
    }
}

if ($failed) {
    Write-Host "FAILED: One or more targeted tests failed." -ForegroundColor Red
    exit 1
}

Write-Host "PASSED: $($uniqueTests.Count) targeted test(s)" -ForegroundColor Green
exit 0
```

#### Step 4.2.4: Create grep-checks.ps1

Create `.claude/hooks/checks/grep-checks.ps1`:

```powershell
# Text pattern checks that custom_lint can't catch
# FROM SPEC: Section 10 — grep checks for patterns not detectable via AST

param()

Write-Host "=== Running grep checks ===" -ForegroundColor Cyan

# Get staged .dart and .sql files
$stagedDart = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.dart$' })
$stagedSql = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.sql$' })
$failed = $false

# Check 1: sync_control writes outside transaction blocks
# FROM SPEC: Section 9 — "sync_control writes outside transaction blocks"
foreach ($file in $stagedDart) {
    $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
    if ($content -match "sync_control" -and $content -notmatch "transaction\s*\(") {
        # Heuristic: if file mentions sync_control but has no transaction() call, flag it
        $lines = Select-String -Path $file -Pattern "sync_control" -SimpleMatch
        foreach ($line in $lines) {
            Write-Host "WARNING: sync_control write may be outside transaction: $($line.Filename):$($line.LineNumber)" -ForegroundColor Yellow
        }
    }
}

# Check 2: change_log DELETE without success guard
# FROM SPEC: Section 9 — "change_log DELETE without success guard"
foreach ($file in $stagedDart) {
    $lines = Select-String -Path $file -Pattern "delete.*change_log|change_log.*delete" -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        # Check surrounding context for success guard
        $content = Get-Content $file -ErrorAction SilentlyContinue
        $lineNum = $line.LineNumber - 1
        $contextStart = [Math]::Max(0, $lineNum - 5)
        $context = $content[$contextStart..$lineNum] -join "`n"
        if ($context -notmatch "rpcSucceeded|success|result\.errors") {
            Write-Host "BLOCKED: change_log DELETE without success guard: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
            $failed = $true
        }
    }
}

# Check 3: Bare threshold literals
# FROM SPEC: Section 9 — "0.85/0.65/0.45 bare threshold literals"
foreach ($file in $stagedDart) {
    $lines = Select-String -Path $file -Pattern '\b0\.(85|65|45)\b' -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        Write-Host "WARNING: Bare threshold literal found — extract to named constant: $($line.Filename):$($line.LineNumber): $($line.Line.Trim())" -ForegroundColor Yellow
    }
}

# Check 4: Hardcoded form type outside registry
# FROM SPEC: Section 9 — "'mdot_0582b' outside builtin_forms.dart"
foreach ($file in $stagedDart) {
    if ($file -match "builtin_forms\.dart$") { continue }
    $lines = Select-String -Path $file -Pattern "mdot_0582b" -SimpleMatch -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        Write-Host "BLOCKED: Hardcoded 'mdot_0582b' outside builtin_forms.dart: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
        $failed = $true
    }
}

# Check 5: AUTOINCREMENT in schema files
# FROM SPEC: Section 9 — "No AUTOINCREMENT in schema"
foreach ($file in ($stagedDart + $stagedSql)) {
    $lines = Select-String -Path $file -Pattern "AUTOINCREMENT" -SimpleMatch -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        Write-Host "BLOCKED: AUTOINCREMENT found: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
        $failed = $true
    }
}

# Check 6: ALTER TABLE without IF EXISTS in .sql files
# FROM SPEC: Section 9 — "ALTER TABLE without IF EXISTS in .sql files"
foreach ($file in $stagedSql) {
    $lines = Select-String -Path $file -Pattern "ALTER\s+TABLE" -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line.Line -notmatch "IF\s+EXISTS") {
            Write-Host "WARNING: ALTER TABLE without IF EXISTS: $($line.Filename):$($line.LineNumber): $($line.Line.Trim())" -ForegroundColor Yellow
        }
    }
}

if ($failed) {
    Write-Host "FAILED: grep checks found blocking issues." -ForegroundColor Red
    exit 1
}

Write-Host "PASSED: grep checks" -ForegroundColor Green
exit 0
```

---

### Sub-phase 4.3: Create New Pre-Commit Orchestrator

**Files:**
- Create: `.claude/hooks/pre-commit.ps1` (replaces archived version)

**Agent**: `general-purpose`

#### Step 4.3.1: Write the orchestrator

Create `.claude/hooks/pre-commit.ps1`:

```powershell
# Pre-commit hook — 3-layer quality gate orchestrator
# FROM SPEC: Section 10 — "main orchestrator (replaces current)"
# Called by .githooks/pre-commit shell shim
#
# Sequence: analyze → custom_lint → grep checks → targeted tests
# ANY failure = hard block (exit 1)

param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$checksDir = Join-Path $scriptDir "checks"

# Get staged .dart files (skip generated)
$stagedFiles = @(git diff --cached --name-only --diff-filter=ACM | Where-Object {
    $_ -match '\.dart$' -and
    $_ -notmatch '\.(g|freezed|mocks)\.dart$'
})

if ($stagedFiles.Count -eq 0) {
    Write-Host "No staged Dart files — skipping pre-commit checks." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Pre-commit: $($stagedFiles.Count) staged Dart file(s)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Step 1: dart analyze
& pwsh -File (Join-Path $checksDir "run-analyze.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

# Step 2: custom_lint
& pwsh -File (Join-Path $checksDir "run-custom-lint.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

# Step 3: grep checks
& pwsh -File (Join-Path $checksDir "grep-checks.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

# Step 4: targeted tests
& pwsh -File (Join-Path $checksDir "run-tests.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "All pre-commit checks passed." -ForegroundColor Green
exit 0
```

<!-- NOTE: .githooks/pre-commit already delegates to this script via `pwsh -ExecutionPolicy Bypass -File ".claude/hooks/pre-commit.ps1"`. No changes needed to the shell shim. -->

---

### Sub-phase 4.4: Verify Pre-Commit Integration

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 4.4.1: Verify shell shim exists

Confirm `.githooks/pre-commit` contains:
```sh
#!/bin/sh
pwsh -ExecutionPolicy Bypass -File ".claude/hooks/pre-commit.ps1"
exit $?
```

#### Step 4.4.2: Verify git hooks path

Run: `pwsh -Command "git config core.hooksPath"`
Expected: `.githooks` (or confirm the shim is in the right location)

#### Step 4.4.3: Smoke test — stage a clean file and commit

```powershell
# Create a trivial change, stage it, attempt commit
# Should pass all 4 checks
```

Run: `pwsh -Command "git stash; git add -A; git stash pop"` (or equivalent dry run)

#### Step 4.4.4: Smoke test — verify violation is blocked

Temporarily add a violation to a staged file (e.g., `Supabase.instance.client` in a presentation file), stage it, and attempt commit. The grep checks or custom_lint should block.

---

## Phase 5: CI & GitHub Automation

### Sub-phase 5.1: Delete Broken Workflows

**Files:**
- Delete: `.github/workflows/e2e-tests.yml`
- Delete: `.github/workflows/nightly-e2e.yml`

**Agent**: `general-purpose`

#### Step 5.1.1: Delete deprecated workflows

```powershell
Remove-Item ".github/workflows/e2e-tests.yml" -Force
Remove-Item ".github/workflows/nightly-e2e.yml" -Force
```

<!-- FROM SPEC: Section 14 — "Delete existing broken workflows" -->
<!-- Ground truth: both files verified to exist -->

---

### Sub-phase 5.2: Create quality-gate.yml

**Files:**
- Create: `.github/workflows/quality-gate.yml`

**Agent**: `general-purpose`

#### Step 5.2.1: Write the main CI workflow

Create `.github/workflows/quality-gate.yml`:

```yaml
name: Quality Gate

on:
  push:
    # NOTE: Cannot combine branches + branches-ignore. Use ignore-only.
    branches-ignore: ['dependabot/**']
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  checks: write

env:
  FLUTTER_VERSION: '3.32.2'

jobs:
  # ============================================
  # Job 1: Analyze + Test (~5 min)
  # FROM SPEC: Section 11 — "Job 1: analyze-and-test"
  # ============================================
  analyze-and-test:
    name: Analyze & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: subosito/flutter-action@v2
        with:
          flutter-version: ${{ env.FLUTTER_VERSION }}
          channel: stable
          cache: true

      - name: Install dependencies
        run: flutter pub get

      # NOTE: No .env file needed — flutter analyze and flutter test do not require
      # runtime Supabase credentials. If tests later need env vars, add creation
      # here with `rm .env` cleanup after tests.

      - name: Dart analyze (zero errors)
        # FROM SPEC: "dart analyze (zero errors — NO --no-fatal-infos flag)"
        run: flutter analyze

      - name: Custom lint check
        run: dart run custom_lint

      - name: Run full test suite
        # FROM SPEC: "flutter test (full suite, all 337+ test files)"
        run: flutter test

  # ============================================
  # Job 2: Architecture Validation (~1 min)
  # FROM SPEC: Section 11 — "Job 2: architecture-validation"
  # ============================================
  architecture-validation:
    name: Architecture Validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: No AUTOINCREMENT in schema
        run: |
          if grep -rn "AUTOINCREMENT" lib/core/database/ supabase/migrations/ 2>/dev/null; then
            echo "::error::AUTOINCREMENT found in schema files"
            exit 1
          fi

      - name: Deprecated screen exports check
        run: |
          if grep -rn "FormsListScreen\|FormFillScreen" lib/ --include="*.dart" 2>/dev/null | grep -v "// deprecated\|@Deprecated\|_deprecated"; then
            echo "::error::Deprecated screen exports found"
            exit 1
          fi

      - name: change_log trigger count matches adapter count
        # FROM SPEC: "change_log trigger count (20) ≈ adapter count (22, minus 2 push-only)"
        run: |
          # WHY: Count entries in triggeredTables list, not string occurrences of triggersForTable
          TRIGGER_COUNT=$(sed -n "/triggeredTables = \[/,/\];/p" lib/core/database/schema/sync_engine_tables.dart | grep -c "'")
          ADAPTER_COUNT=$(grep -c "Adapter()" lib/features/sync/engine/sync_registry.dart 2>/dev/null || echo 0)
          echo "Triggers: $TRIGGER_COUNT, Adapters: $ADAPTER_COUNT"
          # Allow ±2 difference (push-only adapters don't have triggers)
          DIFF=$((ADAPTER_COUNT - TRIGGER_COUNT))
          if [ "$DIFF" -lt 0 ] || [ "$DIFF" -gt 3 ]; then
            echo "::error::Trigger/adapter count mismatch: $TRIGGER_COUNT triggers vs $ADAPTER_COUNT adapters"
            exit 1
          fi

      - name: FK index verification
        run: |
          # Check that REFERENCES columns have matching CREATE INDEX
          echo "FK index check — scanning migrations..."
          REFS=$(grep -rn "REFERENCES" lib/core/database/database_service.dart supabase/migrations/ 2>/dev/null | grep -oP '\w+(?=\s+TEXT\s+REFERENCES|\s+INTEGER\s+REFERENCES)' || true)
          MISSING=0
          for col in $REFS; do
            if ! grep -rq "CREATE INDEX.*$col" lib/core/database/database_service.dart supabase/migrations/ 2>/dev/null; then
              echo "::warning::Missing index for FK column: $col"
              MISSING=$((MISSING + 1))
            fi
          done
          if [ "$MISSING" -gt 0 ]; then
            echo "::warning::$MISSING FK columns without indexes"
          fi

      - name: Schema column consistency (D9)
        # FROM SPEC: D9 — "fromMap keys must match SQL DDL columns"
        # Cross-file analysis: parse fromMap() keys in model files, check against
        # CREATE TABLE columns in database_service.dart and migrations.
        run: |
          echo "D9: Schema column consistency check..."
          # Extract CREATE TABLE column names from schema files
          SCHEMA_COLS=$(grep -oP "(?<=')[a-z_]+(?='\s+(TEXT|INTEGER|REAL|BLOB))" lib/core/database/database_service.dart 2>/dev/null || true)
          # Extract fromMap key strings from model files
          FROMMAP_KEYS=$(grep -rn "fromMap\|from_map" lib/features/*/data/models/*.dart 2>/dev/null | grep -oP "(?<=\[')[a-z_]+(?='\])" || true)
          # Compare (basic: flag fromMap keys not found in any schema)
          MISSING=0
          for key in $FROMMAP_KEYS; do
            if ! echo "$SCHEMA_COLS" | grep -qw "$key" 2>/dev/null; then
              echo "::warning::fromMap key '$key' not found in schema columns"
              MISSING=$((MISSING + 1))
            fi
          done
          if [ "$MISSING" -gt 0 ]; then
            echo "::error::D9: $MISSING fromMap keys don't match schema columns"
            exit 1
          fi
          echo "D9: All fromMap keys match schema columns"

      - name: RLS column existence (S9)
        # FROM SPEC: S9 — "RLS policy columns must exist in target table"
        run: |
          echo "S9: RLS column existence check..."
          # Parse RLS policies from migration files for column references
          # and verify those columns exist in the target table's CREATE TABLE
          VIOLATIONS=0
          for policy_file in supabase/migrations/*.sql; do
            [ -f "$policy_file" ] || continue
            # Extract USING/WITH CHECK clauses and their column refs
            POLICY_COLS=$(grep -oP '(?<=USING\s*\().*?(?=\))' "$policy_file" 2>/dev/null | grep -oP '[a-z_]+(?=\s*=)' || true)
            for col in $POLICY_COLS; do
              TABLE=$(grep -B5 "CREATE POLICY.*USING.*$col" "$policy_file" 2>/dev/null | grep -oP '(?<=ON\s)\w+' || true)
              if [ -n "$TABLE" ]; then
                if ! grep -q "CREATE TABLE.*$TABLE" supabase/migrations/*.sql 2>/dev/null | grep -q "$col"; then
                  echo "::warning::RLS policy references column '$col' on table '$TABLE' — verify column exists"
                  VIOLATIONS=$((VIOLATIONS + 1))
                fi
              fi
            done
          done
          if [ "$VIOLATIONS" -gt 0 ]; then
            echo "::error::S9: $VIOLATIONS RLS column existence warnings"
            exit 1
          fi
          echo "S9: RLS column check passed"

      - name: Dead barrel export detection
        # FROM SPEC: Section 9 — "Dead barrel exports (zero consumers)"
        run: |
          echo "Checking for dead barrel exports..."
          DEAD=0
          for barrel in $(find lib/ -name "*.dart" -exec grep -l "^export " {} \; 2>/dev/null); do
            BARREL_PKG=$(echo "$barrel" | sed 's|^lib/|package:construction_inspector/|')
            IMPORTERS=$(grep -rn "import.*${BARREL_PKG}" lib/ --include="*.dart" 2>/dev/null | wc -l || echo 0)
            if [ "$IMPORTERS" -eq 0 ]; then
              echo "::warning::Dead barrel export (zero importers): $barrel"
              DEAD=$((DEAD + 1))
            fi
          done
          if [ "$DEAD" -gt 0 ]; then
            echo "::warning::$DEAD dead barrel export(s) found"
          fi

  # ============================================
  # Job 3: Security Scanning (~1 min)
  # FROM SPEC: Section 11 — "Job 3: security-scanning"
  # ============================================
  security-scanning:
    name: Security Scanning
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Supabase singleton audit
        # FROM SPEC: "Supabase singleton usage audit (must be zero outside DI root)"
        run: |
          VIOLATIONS=$(grep -rn "Supabase\.instance\.client" lib/ --include="*.dart" \
            | grep -v "app_initializer\.dart" \
            | grep -v "background_sync_handler\.dart" \
            | grep -v "// ignore: avoid_supabase_singleton" || true)
          if [ -n "$VIOLATIONS" ]; then
            echo "::error::Supabase.instance.client violations found outside DI root:"
            echo "$VIOLATIONS"
            exit 1
          fi

      - name: Raw database.delete() audit
        # FROM SPEC: "Raw database.delete() outside SoftDeleteService (must be zero)"
        run: |
          VIOLATIONS=$(grep -rn "database\.delete\|\.delete(" lib/ --include="*.dart" \
            | grep -v "soft_delete_service\.dart" \
            | grep -v "generic_local_datasource\.dart" \
            | grep -v "sync/engine/" \
            | grep -v "change_log\|change_tracker\|sync_control" \
            | grep -v "// ignore: avoid_raw_database_delete" || true)
          # Filter to only actual database.delete calls (heuristic)
          REAL=$(echo "$VIOLATIONS" | grep -i "database\.\|db\.\|txn\." || true)
          if [ -n "$REAL" ]; then
            echo "::warning::Potential raw database.delete() calls found:"
            echo "$REAL"
          fi

      - name: Path traversal guard audit
        run: |
          VIOLATIONS=$(grep -rn "\.contains('\.\.')" lib/ --include="*.dart" \
            | grep -v "path\.normalize" || true)
          if [ -n "$VIOLATIONS" ]; then
            echo "::warning::Weak path traversal guard (contains('..') without normalize):"
            echo "$VIOLATIONS"
          fi

      - name: sync_control transaction boundary check
        run: |
          # Files that write to sync_control should do so inside try/finally
          FILES=$(grep -rln "sync_control" lib/ --include="*.dart" 2>/dev/null || true)
          for file in $FILES; do
            if grep -q "sync_control.*value.*=.*'1'" "$file" 2>/dev/null; then
              if ! grep -q "finally" "$file" 2>/dev/null; then
                echo "::warning::sync_control write without try/finally in $file"
              fi
            fi
          done

      - name: change_log cleanup success-guard check
        run: |
          VIOLATIONS=$(grep -rn "delete.*change_log\|change_log.*delete" lib/ --include="*.dart" 2>/dev/null \
            | grep -v "rpcSucceeded\|success\|result\.errors" || true)
          if [ -n "$VIOLATIONS" ]; then
            echo "::warning::change_log DELETE without success guard:"
            echo "$VIOLATIONS"
          fi
```

---

### Sub-phase 5.3: Create labeler.yml

**Files:**
- Create: `.github/workflows/labeler.yml`
- Create: `.github/labeler.yml`

**Agent**: `general-purpose`

#### Step 5.3.1: Create labeler workflow

Create `.github/workflows/labeler.yml`:

```yaml
name: PR Labeler

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v5
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
```

#### Step 5.3.2: Create label config

Create `.github/labeler.yml`:

```yaml
# FROM SPEC: Section 11 — PR auto-labeling by changed file paths
sync:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/sync/**'

pdf:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/pdf/**'

auth:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/auth/**'

database:
  - changed-files:
    - any-glob-to-any-file: 'lib/core/database/**'

ui:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/*/presentation/**'

tests:
  - changed-files:
    - any-glob-to-any-file: 'test/**'

config:
  - changed-files:
    - any-glob-to-any-file:
      - '.github/**'
      - 'analysis_options.yaml'
      - 'pubspec.yaml'
```

---

### Sub-phase 5.4: Create sync-defects.yml

**Files:**
- Create: `.github/workflows/sync-defects.yml`

**Agent**: `general-purpose`

#### Step 5.4.1: Write the defect sync workflow

Create `.github/workflows/sync-defects.yml`:

```yaml
name: Sync Defects to Issues

# FROM SPEC: Section 11 — "defect-to-GitHub-Issues sync"
on:
  push:
    branches: [main]
    paths:
      - '.claude/defects/**'

permissions:
  issues: write
  contents: read

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Parse and sync defects
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const glob = require('@actions/glob');

            const globber = await glob.create('.claude/defects/_defects-*.md');
            const files = await globber.glob();

            for (const file of files) {
              const content = fs.readFileSync(file, 'utf8');
              const feature = file.match(/_defects-(\w+)\.md/)?.[1] || 'unknown';

              // Parse defect entries (## headers)
              const defects = content.split(/^## /m).slice(1);

              for (const defect of defects) {
                const title = defect.split('\n')[0].trim();
                const body = defect.split('\n').slice(1).join('\n').trim();
                const issueTitle = `[${feature}] ${title}`;

                // Check if issue already exists
                const { data: existing } = await github.rest.issues.listForRepo({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  state: 'all',
                  labels: `defect,${feature}`,
                  per_page: 100,
                });

                const match = existing.find(i => i.title === issueTitle);

                if (!match) {
                  // Create new issue
                  await github.rest.issues.create({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    title: issueTitle,
                    body: `*Auto-synced from \`.claude/defects/_defects-${feature}.md\`*\n\n${body}`,
                    labels: ['defect', feature],
                  });
                  console.log(`Created issue: ${issueTitle}`);
                }
              }
            }
```

---

### Sub-phase 5.5: Create stale-branches.yml

**Files:**
- Create: `.github/workflows/stale-branches.yml`

**Agent**: `general-purpose`

#### Step 5.5.1: Write the branch cleanup workflow

Create `.github/workflows/stale-branches.yml`:

```yaml
name: Clean Up Merged Branches

# FROM SPEC: Section 11 — "Auto-deletes the source branch after merge"
on:
  pull_request:
    types: [closed]

permissions:
  contents: write

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Delete merged branch
        uses: actions/github-script@v7
        with:
          script: |
            const branch = context.payload.pull_request.head.ref;
            if (branch === 'main' || branch === 'master' || branch === 'develop'
                || branch.startsWith('release/') || branch.startsWith('hotfix/')) {
              console.log(`Skipping protected branch: ${branch}`);
              return;
            }
            try {
              await github.rest.git.deleteRef({
                owner: context.repo.owner,
                repo: context.repo.repo,
                ref: `heads/${branch}`,
              });
              console.log(`Deleted branch: ${branch}`);
            } catch (e) {
              console.log(`Branch ${branch} already deleted or protected: ${e.message}`);
            }
```

---

### Sub-phase 5.6: Create dependabot.yml

**Files:**
- Create: `.github/dependabot.yml`

**Agent**: `general-purpose`

#### Step 5.6.1: Write dependabot config

Create `.github/dependabot.yml`:

```yaml
# FROM SPEC: Section 11 — "Weekly pub dependency updates"
version: 2
updates:
  - package-ecosystem: "pub"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
    open-pull-requests-limit: 5
```

---

### Sub-phase 5.7: Verify CI Workflows

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 5.7.1: Validate YAML syntax

Run: `pwsh -Command "Get-ChildItem .github/workflows/*.yml | ForEach-Object { Write-Host $_.Name; python3 -c \"import yaml; yaml.safe_load(open('$($_.FullName)'))\"; if (\$LASTEXITCODE -ne 0) { Write-Host 'INVALID' -ForegroundColor Red } else { Write-Host 'OK' -ForegroundColor Green } }"`

Or manually validate each YAML file.

#### Step 5.7.2: Push to test branch and verify

After committing all changes:
1. Create a feature branch
2. Push to remote
3. Verify `quality-gate.yml` triggers on push
4. Create a PR to main
5. Verify all 3 jobs run: `analyze-and-test`, `architecture-validation`, `security-scanning`
6. Verify labeler applies labels based on changed file paths

---

## Phase 6: Branch Protection + Rule/Doc Updates

### Sub-phase 6.1: Configure Branch Protection

**Files:** None (GitHub API configuration)

**Agent**: `general-purpose`

#### Step 6.1.1: Set branch protection rules via gh CLI

```powershell
# FROM SPEC: Section 12 — Branch protection for main
gh api repos/{owner}/{repo}/branches/main/protection -X PUT --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["analyze-and-test", "architecture-validation", "security-scanning"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

<!-- NOTE: The implementing agent must replace {owner}/{repo} with the actual values: RobertoChavez2433/construction-inspector-tracking-app -->

#### Step 6.1.2: Enable auto-delete head branches

```powershell
# FROM SPEC: Section 12 — "Auto-delete head branches"
gh api repos/{owner}/{repo} -X PATCH -f delete_branch_on_merge=true
```

#### Step 6.1.3: Verify branch protection

Run: `pwsh -Command "gh api repos/RobertoChavez2433/construction-inspector-tracking-app/branches/main/protection --jq '.required_status_checks.contexts[]'"`
Expected: Lists `analyze-and-test`, `architecture-validation`, `security-scanning`

---

### Sub-phase 6.2: Update Rule/Doc Files

**Files:**
- Modify: `.claude/rules/database/schema-patterns.md`
- Modify: `.claude/rules/architecture.md`
- Modify: `.claude/rules/frontend/flutter-ui.md`
- Modify: `.claude/rules/sync/sync-patterns.md`
- Modify: `.claude/rules/testing/patrol-testing.md`

**Agent**: `general-purpose`

#### Step 6.2.1: Update schema-patterns.md

Remove any reference to `is_deleted INTEGER DEFAULT 0`. The column does NOT exist — only `deleted_at` and `deleted_by` are used.

<!-- FROM SPEC: Section 16 — "Remove is_deleted INTEGER DEFAULT 0 — column doesn't exist" -->

#### Step 6.2.2: Update architecture.md

Add an "Anti-Patterns (Enforced by Lint)" section:

```markdown
## Anti-Patterns (Enforced by Lint)

These patterns are enforced by `field_guide_lints` custom lint rules. Violations block commit and CI.

| Anti-Pattern | Rule | Fix |
|-------------|------|-----|
| `Supabase.instance.client` outside DI root | A1 | Inject via constructor from AppInitializer |
| `DatabaseService()` outside DI root | A2 | Inject via constructor |
| Raw SQL in presentation/ | A3 | Use repository/datasource methods |
| Raw SQL in di/ files | A4 | Move to repository layer |
| Datasource imports in presentation/ | A5 | Import repository, not datasource |
| Business logic (await/try) in di/ files | A6 | Move to use case or repository |
| Provider construction outside buildAppProviders() | A7 | Register in app_providers.dart |
| Service construction in widgets | A8 | Inject via Provider.of or context.read |
| Silent catch blocks | A9 | Add Logger.<category>() call |
| `AppTheme.*` color constants | A12 | Use three-tier color system |
| Hardcoded `Colors.*` in presentation | A13 | Use theme tokens |
```

#### Step 6.2.3: Update flutter-ui.md

Add accessibility section:

```markdown
## Accessibility

- **Touch targets**: Minimum 48dp × 48dp for all interactive elements
- **Semantics labels**: All icons and images must have `Semantics` or `semanticLabel`
- **Color contrast**: Use theme tokens (three-tier system) which are designed for contrast
- **Dark mode testing**: All UI must be verified in dark, light, and high-contrast themes
```

Strengthen color rule to reference lint enforcement:

```markdown
## Color System (Enforced by A12, A13)

Colors MUST use the three-tier system. Violations are blocked by custom lint rules.
See spec Section 3 for the full tier mapping.
```

#### Step 6.2.4: Update sync-patterns.md

Add enforced invariants:

```markdown
## Enforced Invariants (Lint Rules)

- **sync_control flag MUST be inside transaction** (S3) — set pulling='1' inside try/finally
- **change_log cleanup MUST be conditional on RPC success** (S2) — never unconditional DELETE
- **ConflictAlgorithm.ignore MUST have rowId==0 fallback** (S1) — check return value, UPDATE on 0
- **No sync_status column** (S4) — deprecated pattern, only change_log is used
- **toMap() MUST include project_id for synced child models** (S5)
- **_lastSyncTime only updated in success path** (S8)
```

#### Step 6.2.5: Update patrol-testing.md

Add deprecated stacks section:

```markdown
## Deprecated Testing Stacks

| Stack | Status | Replacement |
|-------|--------|-------------|
| Patrol | Removed | Unit/widget tests + manual ADB testing |
| flutter_driver | Removed | Unit/widget tests + manual ADB testing |

**Lint rule T6** blocks imports of `patrol` or `flutter_driver` packages.
```

---

### Sub-phase 6.3: End-to-End Verification

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 6.3.1: Full local verification

Run in sequence:
1. `pwsh -Command "flutter pub get"`
2. `pwsh -Command "flutter analyze"` — expect zero issues
3. `pwsh -Command "dart run custom_lint"` — expect zero violations
4. `pwsh -Command "flutter test"` — expect all pass

#### Step 6.3.2: Pre-commit verification

Stage a file and attempt commit. All 4 check scripts should run and pass.

#### Step 6.3.3: CI verification

Push to feature branch, create PR to main. Verify:
- All 3 quality-gate jobs pass
- Labels auto-applied
- Branch protection requires CI pass before merge

#### Step 6.3.4: Merge workflow verification

After CI passes, merge the PR. Verify:
- Branch auto-deleted after merge
- Main branch has all changes
