# Architecture — Procedure Guide

> Loaded on-demand by workers. For constraints and invariants, see .claude/rules/architecture.md

## Layer Architecture

The app follows a **Feature-First Clean Architecture** with clear separation. Clean architecture (domain layer, use cases, repository interfaces) is the norm across **nearly all 17 features** following the S676 refactor.

```
lib/
├── core/        # Cross-cutting (router, theme, config, database)
│   └── database/
│       └── schema/  # Schema files organized by domain
├── shared/      # Base classes, common utilities
├── features/    # 17 feature modules (auth, calculator, contractors, dashboard, entries,
│   │            # forms, gallery, locations, pdf, photos, projects, quantities,
│   │            # settings, sync, todos, toolbox, weather)
│   └── [feature]/
│       ├── data/         # Models, repositories (impl), datasources
│       │   ├── datasources/
│       │   │   ├── local/   # SQLite datasource
│       │   │   └── remote/  # Supabase datasource
│       │   ├── models/      # Data transfer objects / entity implementations
│       │   └── repositories/ # Repository implementations
│       ├── domain/       # Pure Dart — no Flutter, no framework deps
│       │   ├── repositories/ # Repository interfaces (abstracts)
│       │   └── usecases/     # Single-responsibility use case classes
│       ├── presentation/ # Flutter UI layer
│       │   ├── providers/    # ChangeNotifier state holders
│       │   ├── screens/      # Full-page widgets
│       │   ├── widgets/      # Reusable sub-widgets
│       │   └── controllers/  # Editing / form controllers
│       └── di/           # Feature-specific provider/DI definitions
│       # Note: calculator/forms/gallery/todos are sub-features of toolbox
└── services/    # Cross-cutting services (photo, image, permission)
```

## Model Pattern

All data models follow a consistent structure. Reference: `lib/features/projects/data/models/project.dart`

### Standard Model Template

1. **Immutable fields** with final keyword
2. **UUID-based IDs** — Auto-generated if not provided
3. **Timestamp management** — `createdAt`, `updatedAt` auto-populated
4. **copyWith()** method for immutable updates
5. **toMap()** for SQLite/JSON serialization
6. **fromMap()** factory for deserialization

Example from `lib/features/contractors/data/models/contractor.dart`:
- Enums defined at file top (e.g., `ContractorType`)
- Helper getters for enum checks (e.g., `isPrime`, `isSub`)

### Nullable vs Required Fields

- Required: `id`, foreign keys, core identifiers
- Nullable: optional metadata, GPS coordinates, timestamps for optional actions

## Database Pattern

Single SQLite database with foreign key relationships. Reference: `lib/core/database/database_service.dart` (schema version 50).

### Table Naming Convention

- Plural snake_case: `daily_entries`, `bid_items`, `entry_personnel`
- Junction tables: `entry_` prefix + related entity

### Indexing Strategy

Indexes on:
- All foreign key columns
- Frequently filtered columns (e.g., `date`)

## Navigation Pattern

Uses **go_router** with shell routes for persistent bottom nav. Reference: `lib/core/router/app_router.dart`

### Route Structure

- **Shell routes**: Screens with bottom navigation bar
- **Full-screen routes**: Wizard flows, detail views without nav bar

### Parameter Passing

- Path parameters for required IDs: `/entry/:projectId/:date`
- Query parameters for optional data: `?locationId=abc`

## State Management

Provider pattern implemented with:
- `ChangeNotifier` for reactive state
- `context.read<T>()` for actions (one-time reads)
- `Consumer<T>` or `context.watch<T>()` for rebuilds

### Loading Pattern

Use `addPostFrameCallback` to load data after widget is built:

```dart
@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _loadData();
  });
}
```

This prevents "setState during build" errors. Reference: `lib/features/entries/presentation/screens/home_screen.dart` (`initState` — `addPostFrameCallback` calling `_loadProjectData`).

### Async Context Safety

Check `mounted` before using context after async operations:

```dart
Future<void> _doSomething() async {
  await someAsyncOperation();
  if (!mounted) return;
  context.read<Provider>().doThing();
}
```

## Provider Initialization Tiers

Providers are registered in strict tier order in `lib/core/di/app_providers.dart`. Misordering causes runtime failures when a provider tries to read a dependency that hasn't been registered yet.

| Tier | What | Notes |
|------|------|-------|
| 0 | Settings, core services (PreferencesService, DatabaseService, PermissionService) | `.value` wrappers for pre-created instances |
| 0.5 | Consent + Support | Optional, spliced by AppBootstrap (may not exist pre-auth) |
| 1 | Datasources | NOT in widget tree -- created imperatively in AppInitializer |
| 2 | Repositories | NOT in widget tree -- passed via typed *Deps containers |
| 3 | Auth (AuthProvider, AppConfigProvider) | Hoisted `.value` wrappers |
| 4 | Feature providers | ORDER MATTERS: forms MUST precede entries (EntryExportProvider reads FormExportProvider) |
| 5 | Sync (SyncCoordinator, SyncLifecycleManager, ProjectSyncHealthProvider) | Depends on auth + feature providers |

Tiers 1-2 are created imperatively in `AppInitializer` and passed via typed dependency containers. They never appear as `Provider<T>` in the widget tree.

### Typed DI Containers

Dependencies are grouped into typed containers defined in `lib/core/di/app_dependencies.dart`:

- `CoreDeps` -- database, preferences, photo/image services, soft-delete (`lib/core/di/core_deps.dart`)
- `AuthDeps` -- AuthService, AuthProvider, AppConfigProvider
- `ProjectDeps` -- project repository, assignment/settings/health providers, use cases
- `EntryDeps` -- daily entry repository, export repository, document service
- `FormDeps` -- form repositories, FormPdfService
- `SyncDeps` -- SyncCoordinator, SyncLifecycleManager
- `FeatureDeps` -- remaining feature repositories (location, contractor, quantity, photo, calculator, todo, pdf, weather)

All composed into `AppDependencies`, which is passed to `buildAppProviders()`. Feature initializers receive their specific *Deps container and return feature-specific deps.

## Anti-Patterns (General)

| Anti-Pattern | Why | Fix |
|--------------|-----|-----|
| `setState()` in `dispose()` | Widget already deactivated | Use `WidgetsBindingObserver` lifecycle |
| `Provider.of(context)` after async | Context may be invalid | Check `mounted` first |
| Hardcoded colors | Inconsistent theming, breaks dark/light variants | Use `Theme.of(context).colorScheme.*` or `FieldGuideColors.of(context).*` |
| `AppTheme.*` color constants | Deprecated — does not adapt to dark/light themes | Use `Theme.of(context).colorScheme.*` or `FieldGuideColors.of(context).*` |
| Skip barrel exports | Breaks imports | Update `models.dart`, `providers.dart` |
| `firstWhere` without `orElse` | Throws on empty | Use `.where(...).firstOrNull` |
| Save in `dispose()` | Context deactivated | Use `WidgetsBindingObserver.didChangeAppLifecycleState` |
| `.first` on empty list | Throws exception | Check `.isEmpty` or use `.firstOrNull` |
| `catch (_)` without logging | Silently swallows errors, makes debugging impossible | Add `Logger.<category>()` call |
| `debugPrint` in production code | Not captured by logging system, no filtering/routing | Use `Logger.<category>()` |
| Raw SQL in presentation layer | Violates separation of concerns, untestable | Move to repository/datasource layer |
| `db.delete()` (raw) | Bypasses soft-delete; banned by lint rule D4 (avoid_raw_database_delete) | `delete()` on any datasource performs soft-delete (sets `deleted_at`). Use `hardDelete()` for permanent removal. All reads auto-filter `deleted_at IS NULL` via GenericLocalDatasource. |

## Offline-First Pattern

### Sync Mechanism

The sync system uses **SQLite triggers** that auto-populate the `change_log` table on any INSERT, UPDATE, or DELETE to tracked tables. There is no per-model `syncStatus` field. The change log drives what gets pushed to Supabase during the next sync cycle.

Reference: `lib/features/sync/` and `lib/core/database/database_service.dart` (trigger definitions).

### Photo Storage

Photos stored locally with:
- `filePath` — Local device path
- `remotePath` — Cloud storage URL (null until synced)

Reference: `lib/features/photos/data/models/photo.dart`

## Color System

Use the correct color lookup pattern based on the semantic meaning:

| Color Need | Correct Pattern |
|------------|----------------|
| Primary brand color | `Theme.of(context).colorScheme.primary` |
| Error / destructive | `Theme.of(context).colorScheme.error` |
| Primary text | `Theme.of(context).colorScheme.onSurface` |
| Secondary / hint text | `Theme.of(context).colorScheme.onSurfaceVariant` |
| Success indicators | `FieldGuideColors.of(context).statusSuccess` |
| Warning indicators | `FieldGuideColors.of(context).statusWarning` |
| Info indicators | `FieldGuideColors.of(context).statusInfo` |
| Elevated surface | `FieldGuideColors.of(context).surfaceElevated` |
| Glass/frosted overlay | `FieldGuideColors.of(context).surfaceGlass` |
| Tertiary text (hints, timestamps) | `FieldGuideColors.of(context).textTertiary` |

`AppTheme.*` constants are **deprecated** — they do not adapt across dark/light/high-contrast themes.

## Barrel Exports

Group related exports in a single file for cleaner imports.

## Enum Handling

Enums serialized/deserialized using `.name` and `.values.byName()`:

```dart
// Serialize
'type': type.name

// Deserialize
type: ContractorType.values.byName(map['type'] as String)
```

Reference: `lib/features/contractors/data/models/contractor.dart`

## Key Packages

| Package | Purpose |
|---------|---------|
| `provider` | State management (ChangeNotifier) |
| `go_router` | Navigation (shell routes, deep links) |
| `supabase_flutter` | Backend / Auth |
| `sqflite` | Local SQLite storage |
| `syncfusion_flutter_pdf` | PDF generation (template filling) |
| `pdfrx` | PDF rendering to images (bundled PDFium, cross-platform consistent) |
| `printing` | PDF preview / rasterization (Windows primary path) |
| `flusseract` | Tesseract OCR via native binding (`packages/flusseract/`) |
| `syncfusion_flutter_pdfviewer` | PDF viewing / rendering |
| `image` | Image preprocessing (grayscale, contrast) |
| `opencv_dart` | Grid line removal via inpainting |
| `xml` | HOCR parsing |

## Known Deviations

### didChangeDependencies for Provider-Dependent Controllers (Bug 3 Fix)
**File:** `lib/features/entries/presentation/screens/home_screen.dart`
**Why:** `ContractorEditingController` requires `DatabaseService` from Provider, which is not available in `initState()`. The standard Loading Pattern (see above) using `addPostFrameCallback` created a race condition causing `LateInitializationError` when build ran before the callback. Moving to `didChangeDependencies` with a `_controllersInitialized` guard is the established Flutter pattern when `context` is required at build time.
**Guard:** `_controllersInitialized` flag prevents re-initialization on dependency changes.

## AppTerminology (Dual-Mode Labels)

`AppTerminology` (`lib/core/config/app_terminology.dart`) switches all UI labels based on `AppTerminology.useMdotTerms`:

| Concept | Local Agency Mode | MDOT Mode |
|---------|------------------|-----------|
| Daily report | IDR (Inspector's Daily Report) | DWR (Daily Work Report) |
| Quantity item | Bid Item | Pay Item |
| Contract change | Contract Modification | Change Order |

Set via `AppTerminology.setMode(mdotMode: bool)` when switching projects. UI code references static getters (e.g., `AppTerminology.bidItem`) -- no conditional logic in screens.

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
| Raw `AlertDialog(` in presentation | A18 | Use `AppDialog.show()` |
| Raw `showDialog(` in presentation | A19 | Use `AppDialog.show()` |
| Raw `showModalBottomSheet(` in presentation | A20 | Use `AppBottomSheet.show()` |
| Raw `Scaffold(` in screen files | A21 | Use `AppScaffold` |
| Direct `ScaffoldMessenger`/`showSnackBar` in presentation | A22 | Use `SnackBarHelper.show*()` |
| Inline `TextStyle(` in presentation | A23 | Use `AppText.*` or textTheme slots |

> **Note:** Rules A10-A11 and additional data safety, sync integrity, and test quality rules are defined in `fg_lint_packages/field_guide_lints/`. The table above covers architecture-specific rules only.

### Lint Rule Path Triggers

Which lint rules activate based on file path. Use this when creating or modifying files to know what constraints apply.

| Path Pattern | Active Rules | Key Constraints |
|-------------|-------------|-----------------|
| `*/presentation/*` | A3, A5, A8, A13, A18, A19, A20, A22, A23, D5 | No raw SQL, no datasource imports, no service construction, no hardcoded Colors, no raw dialogs/sheets/snackbars/TextStyle, mounted check required |
| `*/presentation/screens/*` | A21 | No raw Scaffold in screen files |
| `*/di/*` | A4, A6, A15 | No raw SQL in DI, no business logic in DI, no duplicate services |
| `*/data/models/*` | S5, D8 | toMap must include project_id for project-scoped features, no sentinel strings |
| `test/*` or `integration_test/*` | T2, T3, T4, T5 | Test rules activate; D3, D11, S1, S3, S4 are EXCLUDED (test-only relaxations) |
| Global (all `lib/**/*.dart`) | A1, A2, A7, A9, A10, A11, A12, A14, A17, D1, D2, D3, D4, D6, D7, D10, S2, S4, S8, T1, T6, T7, T8 | Always enforced regardless of path |

## Design System Token System (Phase 1 of overhaul)

`lib/core/design_system/tokens/` defines five `ThemeExtension` token sets. All are accessed via `.of(context)` and adapt across light/dark themes (high-contrast theme was removed during the overhaul — only light + dark exist).

| ThemeExtension | File | Fields | Variants |
|----------------|------|--------|----------|
| `FieldGuideColors` | `field_guide_colors.dart` | `statusSuccess`, `statusWarning`, `statusInfo`, `surfaceElevated`, `surfaceGlass`, `textTertiary`, ... | light, dark |
| `FieldGuideSpacing` | `field_guide_spacing.dart` | `xs (4)`, `sm (8)`, `md (16)`, `lg (24)`, `xl (32)`, `xxl (48)` | `standard`, `compact` (density-based, not theme-based) |
| `FieldGuideRadii` | `field_guide_radii.dart` | `xs`, `sm`, `md`, `lg`, `xl`, `pill` | shared |
| `FieldGuideMotion` | `field_guide_motion.dart` | `fast (150)`, `normal (300)`, `slow (500)`, `pageTransition (350)`, curves (`curveStandard`, `curveDecelerate`, `curveEmphasized`, `curveAccelerate`, `curveBounce`, `curveSpring`) | `standard`, `reduced` (accessibility) |
| `FieldGuideShadows` | `field_guide_shadows.dart` | `low`, `medium`, `high` | light, dark |

### Usage Examples

```dart
// Spacing
final spacing = FieldGuideSpacing.of(context);
Padding(padding: EdgeInsets.all(spacing.md), child: ...)
SizedBox(height: spacing.lg)

// Radii
final radii = FieldGuideRadii.of(context);
Container(decoration: BoxDecoration(borderRadius: BorderRadius.circular(radii.md)))

// Motion (always check reduce-motion variant via FieldGuideMotion, not raw Duration)
final motion = FieldGuideMotion.of(context);
AnimatedContainer(duration: motion.normal, curve: motion.curveStandard, ...)

// Colors
final fg = FieldGuideColors.of(context);
Icon(Icons.check, color: fg.statusSuccess)
```

Raw `EdgeInsets`, `BorderRadius.circular(...)`, hardcoded `Duration`, and `Colors.*` literals are lint-banned in `lib/**/presentation/**` (rules `no_hardcoded_spacing`, `no_hardcoded_radius`, `no_hardcoded_duration`, `no_hardcoded_colors`).

## Responsive Layout (Phase 2 of overhaul)

`lib/core/design_system/layout/` provides Material 3 responsive primitives. Use these instead of raw `MediaQuery.of(context).size.width` checks.

| Widget / API | File | Purpose |
|--------------|------|---------|
| `AppBreakpoint` enum | `app_breakpoint.dart` | `compact (0-599)`, `medium (600-839)`, `expanded (840-1199)`, `large (1200+)` — `AppBreakpoint.of(context)` returns current bucket |
| `AppResponsiveBuilder` | `app_responsive_builder.dart` | Builder that yields `(context, breakpoint)` so subtrees can branch on form factor |
| `AppAdaptiveLayout` | `app_adaptive_layout.dart` | Picks a child by breakpoint (e.g., bottom-nav on compact, navigation rail on expanded+) |
| `AppResponsiveGrid` | `app_responsive_grid.dart` | Auto-column grid with breakpoint-aware column counts |
| `AppResponsivePadding` | `app_responsive_padding.dart` | Page-level padding that scales with breakpoint |

### Pattern: branching by form factor

```dart
AppResponsiveBuilder(
  builder: (context, bp) {
    if (bp.isCompact) return _PhoneLayout();
    if (bp.isMediumOrLarger) return _TabletLayout();
    return _DesktopLayout();
  },
)
```

Always read breakpoint from `AppBreakpoint.of(context)` (uses `MediaQuery.sizeOf` to avoid keyboard-inset rebuilds), never raw width comparisons.

## Component Inventory (Phase 3 of overhaul)

`lib/core/design_system/` is organized atomically. ~57 components total. See `.claude/state/audit-2026-04-07-phases-1-4.md` for the audit trail.

| Layer | Count | Examples |
|-------|-------|----------|
| `tokens/` | 6 token sets + legacy `design_constants.dart` | `FieldGuideSpacing/Radii/Motion/Shadows/Colors` |
| `atoms/` | 11 | `AppButton`, `AppBadge`, `AppChip`, `AppDivider`, `AppIcon`, `AppText`, `AppToggle`, `AppTooltip`, `AppAvatar`, `AppMiniSpinner`, `AppProgressBar` |
| `molecules/` | 8 | `AppCounterField`, `AppDatePicker`, `AppDropdown`, `AppListTile`, `AppSearchBar`, `AppSectionHeader`, `AppTabBar`, `AppTextField` |
| `organisms/` | 12 | `AppActionCard`, `AppFormFieldGroup`, `AppFormSection`, `AppFormSectionNav`, `AppFormStatusBar`, `AppFormSummaryTile`, `AppFormThumbnail`, `AppGlassCard`, `AppInfoBanner`, `AppPhotoGrid`, `AppSectionCard`, `AppStatCard` |
| `surfaces/` | 6 | `AppScaffold`, `AppDialog`, `AppBottomSheet`, `AppBottomBar`, `AppDragHandle`, `AppStickyHeader` |
| `feedback/` | 7 | `AppBanner`, `AppBudgetWarningChip`, `AppContextualFeedback`, `AppEmptyState`, `AppErrorState`, `AppLoadingState`, `AppSnackbar` |
| `layout/` | 5 | `AppAdaptiveLayout`, `AppBreakpoint`, `AppResponsiveBuilder`, `AppResponsiveGrid`, `AppResponsivePadding` |
| `animation/` | 4 + 4 helpers | `AppAnimatedEntrance`, `AppContainerTransform`, `AppStaggeredList`, `AppTapFeedback` (+ `AppValueTransition`, `MotionAware`, `SharedAxisTransitionPage`) |

When choosing a widget, descend in atomic order: prefer an existing organism > molecule > atom > raw widget. Raw Material widgets in presentation/ are lint-banned for all categories listed above.

## Sync Observability Pattern (Phase 4 of overhaul)

Long-edit screens (wizards, draft editors, multi-step forms) extract a `ChangeNotifier` controller per screen and register it with `WizardActivityTracker` (`lib/features/sync/application/wizard_activity_tracker.dart`). This lets `SyncCoordinator` query in-flight UI state before sync cycles and defer sync that would clobber unsaved drafts.

### Why

- Sync engine pulls remote state and overwrites local rows. If a wizard draft is open and dirty, a pull mid-edit can overwrite it.
- Without an observable signal, sync code would have to reach into widgets — a layering violation.
- `WizardActivityTracker` is a thin `ChangeNotifier` registry: controllers register/unregister, sync reads.

### Pattern

```dart
class ProjectSetupController extends ChangeNotifier {
  ProjectSetupController(this._tracker) {
    _tracker.register(
      key: _wizardKey,
      label: 'New project setup',
      hasUnsavedChanges: () => _hasUnsavedDraft,
    );
  }

  static const _wizardKey = 'project-setup';
  final WizardActivityTracker _tracker;
  bool _hasUnsavedDraft = false;

  void onFieldChanged() {
    _hasUnsavedDraft = true;
    _tracker.markChanged(_wizardKey);
    notifyListeners();
  }

  @override
  void dispose() {
    _tracker.unregister(_wizardKey);
    super.dispose();
  }
}
```

Examples in repo: `lib/features/projects/presentation/controllers/project_setup_controller.dart`, `lib/features/pdf/presentation/controllers/pdf_import_controller.dart`, `lib/features/quantities/presentation/controllers/quantity_calculator_controller.dart`, `lib/features/pay_applications/presentation/controllers/pay_app_detail_controller.dart`.

`SyncCoordinator` consumes the tracker via `hasUnsavedWizard` before deciding to push/pull. Do not invent ad-hoc globals or reach into widget state from sync code.
