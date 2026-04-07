# Worker Rules

Static context for implementer and fixer agents. Appended via `--append-system-prompt-file`.

## Agent Behavior Rules
- NEVER use // ignore: comments — always fix root cause
- NEVER write TODO stubs — every test must have real assertions
- NEVER write dead code — no unused imports, variables, classes
- NEVER run flutter clean
- NEVER add Co-Authored-By lines
- NEVER use Bash for anything except: `pwsh -Command "flutter analyze"`, `pwsh -Command "dart run custom_lint"`
- Read each target file before editing to preserve existing content
- Implement EXACTLY what the plan specifies — no additions, no omissions
- Reuse shared test helpers (check test/helpers/ before creating fakes/mocks)
- All Given/When/Then skeletons MUST be filled with actual test code

## Lint Verification
After completing all implementation substeps, run BOTH:
1. `pwsh -Command "flutter analyze"`
2. `pwsh -Command "dart run custom_lint"`
Fix any violations before reporting completion. NEVER suppress with // ignore:.

## Project Architecture (curated)
- Feature-first Clean Architecture: data/domain/presentation per feature
- State: ChangeNotifier via provider package (~32 providers)
- Data flow: Screen -> Provider -> UseCase -> Repository -> Datasource -> SQLite -> Supabase
- Soft-delete default: delete() = soft-delete, hardDelete() for permanent
- change_log is trigger-only (20 tables, gated by sync_control.pulling='0')
- Provider tiers 1-2 NOT in widget tree (created in AppInitializer)
- is_builtin=1 rows are server-seeded (triggers skip, cascade skip, push skip)
- PRAGMAs via rawQuery (Android API 36 rejects via execute())
- Git Bash silently fails on Flutter — always use `pwsh -Command "..."`

## Lint Rules (key subset)
- No raw SQL in presentation/ or di/
- No datasource imports in presentation/
- No service construction in widgets
- No hardcoded Colors.* in presentation (use theme tokens)
- No raw Scaffold in screens (use AppScaffold)
- No raw AlertDialog/showDialog (use AppDialog.show())
- No silent catch blocks (add Logger call)
- No db.delete() (use soft-delete via datasource)

## Design System Token Rules (lint-enforced)
NEVER write raw literals for spacing, radii, motion, or text styles in `lib/**/presentation/**`. Always go through the ThemeExtension accessor.

| Banned | Replacement |
|--------|-------------|
| `EdgeInsets.all(16)`, `EdgeInsets.symmetric(...)` with literals | `EdgeInsets.all(FieldGuideSpacing.of(context).md)` |
| `SizedBox(height: 8)` literal gaps | `SizedBox(height: FieldGuideSpacing.of(context).sm)` |
| `BorderRadius.circular(12)`, `Radius.circular(8)` | `BorderRadius.circular(FieldGuideRadii.of(context).md)` |
| `Duration(milliseconds: 300)` in animations | `FieldGuideMotion.of(context).normal` |
| Inline `TextStyle(...)` | `AppText.*` variant or `Theme.of(context).textTheme.*` slot |
| `Colors.red`, `Color(0xFF...)` | `Theme.of(context).colorScheme.*` or `FieldGuideColors.of(context).*` |

The high-contrast theme has been removed. Only light + dark variants exist on `FieldGuideColors`/`FieldGuideShadows`.

## Component Selection Rules (10 design-system lint rules)
Prefer the design system widget over the raw Material widget. Lint will reject raw usage in presentation/.

1. `no_raw_button` — use `AppButton.primary/secondary/tertiary/icon` instead of `ElevatedButton`/`TextButton`/`OutlinedButton`/`FilledButton`/`IconButton`.
2. `no_raw_divider` — use `AppDivider` instead of `Divider`/`VerticalDivider`.
3. `no_raw_tooltip` — use `AppTooltip` instead of `Tooltip`.
4. `no_raw_dropdown` — use `AppDropdown` instead of `DropdownButton`/`DropdownButtonFormField`.
5. `no_raw_snackbar` — use `SnackBarHelper.show*()` / `AppSnackbar` instead of constructing `SnackBar(...)`.
6. `no_hardcoded_spacing` — use `FieldGuideSpacing.of(context).*` instead of literal padding/SizedBox.
7. `no_hardcoded_radius` — use `FieldGuideRadii.of(context).*` instead of `BorderRadius.circular(N)`.
8. `no_hardcoded_duration` — use `FieldGuideMotion.of(context).*` instead of `Duration(milliseconds: N)` in animation contexts.
9. `no_raw_navigator` (INFO) — use GoRouter (`context.go/push`) instead of `Navigator.of(context).push/pop` for routed flows.
10. `prefer_design_system_banner` — use `AppBanner` instead of inline `Container`/`MaterialBanner` for inline notifications.

Also continue to follow the pre-existing rules: `no_raw_scaffold` (use `AppScaffold`), `no_raw_alert_dialog` / `no_raw_show_dialog` (use `AppDialog.show()`), `no_raw_bottom_sheet` (use `AppBottomSheet.show()`), `no_inline_text_style`, `no_raw_text_field`.

## Responsive Layout Rules
- NEVER read `MediaQuery.of(context).size.width` to branch layouts. Use `AppBreakpoint.of(context)` (compact/medium/expanded/large).
- For form-factor branching, use `AppResponsiveBuilder` or `AppAdaptiveLayout` from `lib/core/design_system/layout/`.
- For multi-column grids, use `AppResponsiveGrid`.
- For page-level padding, use `AppResponsivePadding` (scales with breakpoint).

## File and Method Size Cap
- HARD CAP: no file exceeds **300 lines**, and no method/build()/extracted widget class exceeds **300 lines**. Decompose by extracting widgets, helper methods, controllers, or mixins. (This supersedes the older 400-line guideline.)

## Sync Observability for Wizard Screens
If you create or modify a multi-step / wizard / long-edit screen, extract a `ChangeNotifier` controller and register it with `WizardActivityTracker` (`lib/features/sync/application/wizard_activity_tracker.dart`):
- `register({key, label, hasUnsavedChanges})` from controller construction or `initState`.
- `markChanged(key)` whenever in-flight state mutates.
- `unregister(key)` from `dispose`.

This is required so `SyncCoordinator` can defer sync that would clobber unsaved drafts. Reference examples: `lib/features/projects/presentation/controllers/project_setup_controller.dart`, `lib/features/pay_applications/presentation/controllers/pay_app_detail_controller.dart`.

## Domain Context Loading
Before starting work, read the applicable rule files based on the files you will modify:

| File pattern | Read before working |
|-------------|-------------------|
| lib/**/data/** | .claude/rules/backend/data-layer.md |
| lib/core/database/** | .claude/rules/database/schema-patterns.md |
| lib/**/presentation/**, lib/shared/widgets/** | .claude/rules/frontend/flutter-ui.md |
| lib/features/sync/** | .claude/rules/sync/sync-patterns.md |
| lib/features/auth/** | .claude/rules/auth/supabase-auth.md |
| lib/features/pdf/** | .claude/rules/pdf/pdf-generation.md |
| test/**, integration_test/** | .claude/rules/testing/patrol-testing.md |
| .github/workflows/** | .claude/rules/ci-cd.md |
| lib/core/di/**, lib/core/bootstrap/**, lib/core/router/** | .claude/rules/architecture.md |
| supabase/** | .claude/rules/backend/supabase-sql.md |
| android/**, ios/**, windows/** | .claude/rules/platform-standards.md |

This is mandatory. Read the matching rule files before writing any code. After loading, print:
[CONTEXT] Domain rules loaded: <filenames>

## Progress Reporting
Print a status line after each sub-step:
```
[PROGRESS] Phase N Step X.Y: DONE — <brief description>
```
