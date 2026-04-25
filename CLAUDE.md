# Field Guide App

Cross-platform Flutter app for construction inspectors. Offline-first SQLite app with optional Supabase sync.

**Security is non-negotiable. Do not bypass approval flows, weaken RLS, or introduce privilege-escalation paths.**

## Startup Context

- Use `.claude/autoload/_state.md` for current session status and next actions.
- Use `.claude/memory/MEMORY.md` only when durable project patterns matter to the task.
- Load only the `.claude/rules/` files that match the surface you are editing.
- Do not preload broad `.claude/docs/` or historical plan files unless the task needs them.

## Working Rules

- Use PowerShell wrappers for Flutter and Dart commands. Do not run Flutter directly in Git Bash.
- Keep `flutter analyze` and `dart run custom_lint` green.
- Do not weaken lint rules, add ignore comments, or widen allowlists just to make a change pass.
- GitHub issues are the defect system of record. Do not create `.claude/defects/*`.
- For non-trivial work, use the repo workflows and plans rather than improvising from scratch.

## Architecture

- Keep the feature-first split: `data/`, `domain/`, `presentation/`, `di/`.
- Use `provider` and `ChangeNotifier` only. Do not introduce Riverpod or a second state-management system.
- Preserve the core flow: screen -> provider -> use case -> repository -> datasource.
- Keep domain code pure Dart. No Flutter imports in `domain/`.
- Build dependencies through the typed DI containers and app bootstrap. No ad-hoc wiring.

## Data And Sync

- Soft delete is the default. Hard delete must stay explicit.
- `change_log` is trigger-owned. Never insert into it manually.
- Do not reintroduce `sync_status` columns or indexes.
- Treat `is_builtin=1` rows as server-seeded data with the existing skip behavior intact.
- Use `SyncCoordinator` as the sync entrypoint.
- `SyncErrorClassifier` owns sync error classification.
- `SyncStatus` is the single source of truth for transport state.

## UI

- Use the design-system owners where the repo already provides them.
- Use theme tokens and color-scheme accessors instead of hardcoded presentation values.
- Check `mounted` after async gaps before using `context`.
- Prefer `AppNavigator` / `context.appGo` / `context.appPush` over raw
  `Navigator`. Route definitions live in `lib/core/router/autoroute/` and
  `lib/core/navigation/`.
- Keep presentation files thin and aligned with the existing controller/provider split.

## Testing

- Test real behavior, not mock presence.
- Do not add test-only methods or lifecycle hooks to production classes.
- Mock only after understanding the real dependency chain and side effects.
- Prefer real production seams over large mock stacks.
- Use `TestingKeys`, not hardcoded `Key('...')`.
- Keep sync-visible UI inspectable through the existing driver contracts.

## Path-Scoped Rules

- `rules/architecture.md`
- `rules/frontend/flutter-ui.md`
- `rules/testing/testing.md`
- `rules/sync/sync-patterns.md`
- `rules/backend/data-layer.md`
- `rules/backend/supabase-sql.md`
- `rules/database/schema-patterns.md`
- `rules/auth/supabase-auth.md`
- `rules/pdf/pdf-generation.md`
- `rules/platform-standards.md`

## On-Demand References

- `.claude/docs/`
- `.claude/skills/`
- `.claude/plans/`
- `.claude/agents/`
