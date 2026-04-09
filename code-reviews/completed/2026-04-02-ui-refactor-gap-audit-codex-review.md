# UI Refactor Gap Audit

Date: 2026-04-02
Author: Codex
Scope: Compare the implemented codebase against:
- `.claude/plans/completed/2026-03-06-ui-refactor-comprehensive.md`
- `.claude/plans/completed/2026-03-28-ui-refactor-v2.md`

## Executive Verdict

The theme foundation and a subset of the design-system groundwork landed, but the March 6 refactor was not fully implemented.

The biggest miss is that the March 6 plan described a structural UI rewrite, especially on the dashboard, while the implemented code mostly performs token/theme migration and selective widget cleanup. The March 28 plan appears to have narrowed that scope further, which explains why the app can look cleaner in places while still feeling like the old UI.

## What Clearly Landed

- `FieldGuideColors` exists and is wired into theme infrastructure.
- `flutter analyze` passes.
- `flutter test` passes.
- `Color(0x` outside `lib/core/theme/` is effectively zero.
- Deprecated `AppTheme` color families were broadly migrated out of feature code.
- Some lower-level design-system pieces are in use:
  - `AppLoadingState`
  - `AppEmptyState`
  - `AppToggle`

## March 6 Plan: Major Gaps

### 1. Dashboard redesign was not delivered as specified

Original requirement:
- Full structural rewrite using the locked "Premium Elevated - Vivid Variant" dashboard mockup
- 3-stat row
- separate "Today's Entry" CTA card
- weather summary card backed by `WeatherProvider`
- compact draft pill below stats
- `AppScaffold`, `AppGlassCard`, `AppSectionHeader`, `AppProgressBar`, `AppText` based composition

Observed implementation:
- Still uses plain `Scaffold` in `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
- Still renders 4 stat cards, including `Contractors`
- No weather card
- No `WeatherProvider` in the repo
- No separate "Today's Entry" card; the entry action remains in the app bar button
- Drafts remain a full-width card instead of a compact pill
- Budget/tracked/alert sections are hand-built containers, not design-system composition

Evidence:
- March 6 dashboard spec: lines 828-850 in `.claude/plans/completed/2026-03-06-ui-refactor-comprehensive.md`
- Current scaffold: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:57`
- Current 4-stat row: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:324-387`
- Drafts card still full card: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:247-321`
- No `WeatherProvider` class anywhere in `lib/`
- Weather DI file only registers `WeatherService`: `lib/features/weather/di/weather_providers.dart`

### 2. Dashboard widget rewrites did not adopt the intended design-system primitives

March 6 required:
- `DashboardStatCard` -> `AppGlassCard`
- `BudgetOverviewCard` -> `AppGlassCard` + `AppProgressBar`
- `TrackedItemRow` -> `AppGlassCard` + `AppProgressBar`
- `AlertItemRow` -> `AppGlassCard` + `AppProgressBar`
- typography via `AppText.*`

Observed implementation:
- All four widgets are still manually composed with `Container`, `BoxDecoration`, `Text`, and `LinearProgressIndicator`
- No production usage of `AppGlassCard`
- No production usage of `AppProgressBar`
- No production usage of `AppSectionHeader`
- No production usage of `AppText`

Evidence:
- `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart`
- `lib/features/dashboard/presentation/widgets/budget_overview_card.dart`
- `lib/features/dashboard/presentation/widgets/tracked_item_row.dart`
- `lib/features/dashboard/presentation/widgets/alert_item_row.dart`
- Production usage counts outside `lib/core/design_system/`:
  - `AppGlassCard`: 0
  - `AppProgressBar`: 0
  - `AppSectionHeader`: 0
  - `AppText`: 0

### 3. Fine-print dashboard requirements from March 6 are still missing

Missing details:
- Contractors stat was supposed to be removed from the main stat row
- Budget card was supposed to sit in hero position directly after stats
- Drafts were supposed to be a compact `AppChip.cyan`
- Project number was supposed to use `projectNumberText`
- Top Tracked and Approaching Limit were supposed to be sectioned with `AppSectionHeader`
- Tracked and alert rows were supposed to show explicit quantities and remaining values
- `AlertItemRow` was supposed to include a progress bar

Observed state:
- Contractors still present in the stat row
- Drafts still use a large review card
- No `AppChip` usage in production
- `TrackedItemRow` only shows used/total
- `AlertItemRow` has no progress bar and no explicit quantity breakdown

Evidence:
- Stat row: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:355-385`
- `TrackedItemRow`: `lib/features/dashboard/presentation/widgets/tracked_item_row.dart:117-120`
- `AlertItemRow`: `lib/features/dashboard/presentation/widgets/alert_item_row.dart:40-69`
- Production `AppChip` usage outside design-system/driver: 0

### 4. The design-system library exists, but large parts were never adopted

This is the clearest "main system exists, rollout incomplete" signal.

Core wrappers with zero production usage:
- `AppScaffold`
- `AppGlassCard`
- `AppProgressBar`
- `AppSectionHeader`
- `AppText`
- `AppTextField`
- `AppBottomSheet.show`
- `AppDialog.show`

This means the library was built, but much of the app was not actually migrated onto it.

### 5. Modal standardization from March 6 did not happen

March 6 Phase 10 promised:
- all bottom sheets via `AppBottomSheet`
- dialogs via `AppDialog`
- shared `ConfirmationDialog` upgraded to T Vivid styling
- no missed dialogs after `showDialog(` sweep

Observed state:
- `showModalBottomSheet(` count: 8
- `showDialog(` count: 19
- `AlertDialog(` count: 62
- `AppBottomSheet.show` production usages: 0
- `AppDialog.show` production usages: 0
- shared confirmation dialog still builds raw `AlertDialog`

Representative raw dialog files:
- `lib/shared/widgets/confirmation_dialog.dart`
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/todos/presentation/screens/todos_screen.dart`
- `lib/features/settings/presentation/widgets/member_detail_sheet.dart`
- `lib/features/projects/presentation/widgets/project_switcher.dart`
- `lib/features/gallery/presentation/screens/gallery_screen.dart`

### 6. Final typography migration from March 6 was not completed

March 6 Phase 12 expected the app to eliminate raw inline typography in feature code.

Observed state:
- `TextStyle(` outside theme/test: 125 callsites

This is not cosmetic only. It means the app is still bypassing the design-system text layer in many places, which weakens consistency and makes theme evolution harder.

### 7. Shared dialog/input migration from March 6 is incomplete

March 6 expected form dialogs to adopt:
- `AppTextField`
- `AppText.*`
- standardized dialog styling

Observed state:
- `AppTextField` has zero production usage
- many dialog-heavy files still rely on raw `AlertDialog` and raw `TextStyle`

Representative examples:
- `lib/shared/widgets/confirmation_dialog.dart`
- `lib/features/projects/presentation/widgets/add_contractor_dialog.dart`
- `lib/features/projects/presentation/widgets/add_location_dialog.dart`
- `lib/features/projects/presentation/widgets/bid_item_dialog.dart`
- `lib/features/entries/presentation/screens/report_widgets/report_add_quantity_dialog.dart`

### 8. March 6 cleanup gates were not fully achieved

Completed:
- no raw `Color(0x` outside theme files
- no remaining deprecated `AppTheme` color-family usage in feature code

Not completed:
- `TextStyle(` remains at 125 callsites
- modal standardization remains incomplete
- snackbar migration remains incomplete
- centralized testing key migration remains incomplete

## March 28 Plan: Shortcomings

### 1. It narrowed the dashboard from a redesign to a token migration

This is the most important shortcoming in the second plan.

March 6 dashboard goal:
- structural redesign
- new composition
- new cards and weather surface

March 28 dashboard goal:
- migrate static colors and inline text styles to `cs` / `tt` / `fg`

Evidence:
- March 6 dashboard rewrite scope: `.claude/plans/completed/2026-03-06-ui-refactor-comprehensive.md:761-859`
- March 28 dashboard scope is mostly token replacement: `.claude/plans/completed/2026-03-28-ui-refactor-v2.md:4451-4705`

Effect:
- The codebase satisfied the later, weaker dashboard definition much more than the original visual rewrite.
- That is why the dashboard can be "refactored" in code terms but still feel visually unchanged.

### 2. The second plan also overestimated design-system adoption

March 28 kept assuming design-system rollout, testing-key migration, snackbar migration, and modal standardization would be completed.

Observed misses:
- `AppGlassCard`, `AppProgressBar`, `AppSectionHeader`, `AppText`, `AppTextField`, `AppScaffold`, `AppDialog`, `AppBottomSheet` still have zero production adoption
- snackbar cleanup expected zero direct calls, but 3 remain
- `ValueKey(` cleanup expected zero remaining inline usages, but 3 remain

Direct snackbar leftovers:
- `lib/features/settings/presentation/screens/help_support_screen.dart:191`
- `lib/features/settings/presentation/screens/consent_screen.dart:103`
- `lib/features/settings/presentation/screens/legal_document_screen.dart:89`

Inline `ValueKey` leftovers:
- `lib/core/router/routes/project_routes.dart:24`
- `lib/features/gallery/presentation/screens/gallery_screen.dart:374`
- `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart:190`

### 3. The second plan's modal migration remains unfinished

March 28 explicitly called for:
- feature dialog sweeps
- report dialog sweeps
- inline `AlertDialog` extraction/migration
- snackbar cleanup inside dialog flows

Observed state:
- raw `AlertDialog` and `showDialog` are still widespread
- `ConfirmationDialog` still uses raw `AlertDialog`
- production usage of `AppDialog.show` and `AppBottomSheet.show` is still zero

### 4. The second plan's final quality gate is only partially true

What passes:
- `flutter analyze`
- `flutter test`
- deprecated `AppTheme` color tokens are mostly gone from feature code
- raw hex colors outside theme are effectively gone

What does not pass:
- zero direct snackbar callsites
- zero inline `ValueKey` usages
- full modal standardization
- true design-system adoption
- full removal of raw inline `TextStyle`

## Additional Cross-Cutting Gaps

### 1. Page transition work from March 6 was not implemented

March 6 Phase 11 called for `CustomTransitionPage` with fade/slide transitions.

Observed state:
- router uses `NoTransitionPage` for the shell routes

Evidence:
- `lib/core/router/app_router.dart:106-125`

### 2. Performance pass is partial, not complete

What landed:
- multiple `RepaintBoundary` additions exist
- dashboard stat cards, tracked item rows, photo thumbnails, draft tiles, and parts of home screen show evidence of this work

What is still unclear or incomplete relative to March 6:
- no evidence that the broader lazy-list conversion was completed across all named screens
- page transitions were not upgraded
- scroll physics are mixed rather than uniformly standardized

## Bottom Line

The repo does not reflect a full implementation of the March 6 UI refactor plan.

What happened instead is:
1. The theme layer and some supporting design-system files were created.
2. Select cleanup and token migration happened.
3. The dashboard and many modal-heavy areas were not rebuilt to the structural level the first plan described.
4. The March 28 plan appears to have reduced ambition in at least one critical area, especially the dashboard.

That combination matches the current outcome:
- the system foundations exist
- the app compiles and tests cleanly
- the dashboard still feels essentially like the old page
- the first plan's "fine print" was not actually carried through
