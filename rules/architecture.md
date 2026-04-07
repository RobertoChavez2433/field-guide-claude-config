---
paths:
  - "lib/**/*.dart"
---

# Architectural Constraints

Feature-first Clean Architecture with provider-only state management, offline-first SQLite with Supabase sync.

## Hard Constraints

- **Feature-first layers**: Each feature has `data/`, `domain/`, `presentation/`, `di/` sub-directories
- **Provider-only state management**: `ChangeNotifier` via `provider` package (~32 providers) — NOT Riverpod
- **Data flow**: Screen -> Provider -> UseCase -> Repository -> Datasource -> SQLite -> Supabase
- **Provider tier ordering** (tiers 0-5): Forms MUST precede entries in tier 4 (`ExportEntryUseCase` depends on `ExportFormUseCase`)
- **Tiers 1-2 are NOT in widget tree** — created imperatively in `AppInitializer`, passed via typed `*Deps` containers
- **Typed DI containers**: CoreDeps, AuthDeps, ProjectDeps, EntryDeps, FormDeps, SyncDeps, FeatureDeps — composed into `AppDependencies`
- **`is_builtin=1` rows are server-seeded** — triggers skip them, cascade-delete skips them, push skips them
- **Domain layer is pure Dart** — no Flutter imports, no framework dependencies

## Key Anti-Patterns

- No raw SQL in presentation/ or di/ layers
- No hardcoded `Colors.*` — use `Theme.of(context).colorScheme.*` or `FieldGuideColors.of(context).*`
- No raw `Scaffold`, `AlertDialog`, `showDialog`, `showModalBottomSheet` — use design system (`AppScaffold`, `AppDialog.show()`, `AppBottomSheet.show()`)
- No `SnackBarHelper` bypass — use `SnackBarHelper.show*()`
- No inline `TextStyle(` — use `AppText.*` or textTheme slots
- No silent `catch` blocks — always log via `Logger.<category>()`
- Check `mounted` after every async gap before using `context`
- No `debugPrint` in production code — use `Logger`

### Design System Lint Rules (Phase 0 of overhaul, lint-enforced)

| Rule | Banned Pattern | Replacement |
|------|----------------|-------------|
| `no_raw_button` | `ElevatedButton`, `TextButton`, `OutlinedButton`, `FilledButton`, `IconButton` | `AppButton.primary` / `AppButton.secondary` / `AppButton.tertiary` / `AppButton.icon` |
| `no_raw_divider` | `Divider(`, `VerticalDivider(` | `AppDivider` |
| `no_raw_tooltip` | `Tooltip(` | `AppTooltip` |
| `no_raw_dropdown` | `DropdownButton`, `DropdownButtonFormField` | `AppDropdown` |
| `no_raw_snackbar` | `SnackBar(` constructor in presentation/ | `SnackBarHelper.show*()` / `AppSnackbar` |
| `no_hardcoded_spacing` | `EdgeInsets.all(16)`, raw `SizedBox(height: 8)`, numeric `padding:` literals | `FieldGuideSpacing.of(context).md` etc. |
| `no_hardcoded_radius` | `BorderRadius.circular(12)`, `Radius.circular(8)` | `FieldGuideRadii.of(context).md` etc. |
| `no_hardcoded_duration` | `Duration(milliseconds: 300)` in animation/transition contexts | `FieldGuideMotion.of(context).normal` etc. |
| `no_raw_navigator` (INFO) | `Navigator.of(context).push/pop` for routed flows | `context.go(...)` / `context.push(...)` via GoRouter |
| `prefer_design_system_banner` | Inline `Container`/`MaterialBanner` for inline notifications | `AppBanner` |

### Token Migration Map (`DesignConstants` → ThemeExtension)

| Legacy | New |
|--------|-----|
| `DesignConstants.space1..space12` | `FieldGuideSpacing.of(context).xs/sm/md/lg/xl/xxl` |
| `DesignConstants.radius*` | `FieldGuideRadii.of(context).xs/sm/md/lg/xl/pill` |
| `DesignConstants.animation*` / curve constants | `FieldGuideMotion.of(context).fast/normal/slow/pageTransition` + curve fields |
| `DesignConstants.elevation*` / shadow lists | `FieldGuideShadows.of(context).low/medium/high` |

`DesignConstants` is retained only as a static fallback for intermediate values not promoted to ThemeExtensions; new code should always go through `.of(context)`.

## Sync Observability

Long-edit screens (wizards, multi-step forms, draft editors) MUST extract a `ChangeNotifier` controller per screen and register it with `WizardActivityTracker` (`lib/features/sync/application/wizard_activity_tracker.dart`).

- Register from controller `init` / screen `initState` with a stable key, label, and `hasUnsavedChanges` callback.
- Unregister from `dispose`.
- Call `markChanged(key)` whenever in-flight state mutates so listeners (e.g. `SyncProvider`) update.
- `SyncCoordinator` consults `hasUnsavedWizard` before push/pull cycles to defer sync that would clobber drafts.

This is the canonical mechanism for making screen state observable to sync; do not invent ad-hoc global flags.

## Navigation

Uses **go_router** with shell routes (persistent bottom nav) and full-screen routes (wizards, detail views). Path params for required IDs, query params for optional data.

## Offline-First

SQLite triggers auto-populate `change_log` on tracked tables. No per-model `syncStatus` field. Change log drives push to Supabase.

> For code patterns, tier details, color system, and lint rule inventory, see `.claude/skills/implement/references/architecture-guide.md`
