# Durable Project Memory

Use this file for stable project patterns and user preferences that are worth
loading on demand. Do not treat it as a session notebook.

## Project Shape

- Field Guide is a Flutter app for construction inspectors.
- The app is offline-first with SQLite as the local source of truth and
  optional Supabase sync.
- Architecture is feature-first with `data/`, `domain/`, `presentation/`, and
  `di/`.

## Implementation Patterns

- Use `provider` and `ChangeNotifier`. Do not introduce Riverpod or another
  state-management stack.
- Keep domain code pure Dart.
- Build dependencies through the typed DI containers and app bootstrap.
- `change_log` is trigger-owned. Do not insert into it manually.
- `SyncCoordinator` is the sync entrypoint.
- `SyncStatus` is the transport-state source of truth.
- Sync-visible UI changes must stay aligned with the driver contract owners in:
  - `lib/core/driver/screen_registry.dart`
  - `lib/core/driver/screen_contract_registry.dart`
  - `lib/core/driver/flow_registry.dart`
  - `lib/core/driver/driver_diagnostics_handler.dart`

## Agent And Workflow Patterns

- Live review agents are:
  - `code-review-agent`
  - `security-agent`
  - `completeness-review-agent`
- `debug-research-agent` is the scoped read-only helper for deep debugging.
- `plan-writer-agent` writes plan fragments from prepared tailor output.
- Implementation now uses generic workers plus rules and skill references, not
  a large fleet of specialist agents.
- Pass full context to subagents. They do not inherit enough state implicitly.
- Top-level orchestration must own any multi-agent fan-out. Do not rely on a
  subagent to dispatch more subagents.
- Parallel agents can stomp each other. Re-read touched files before assuming a
  worker result is still current.

## Testing Preferences

- Favor real-behavior tests over mock-behavior tests.
- Do not add test-only methods or cleanup APIs to production classes.
- Mock only after understanding the full dependency chain and side effects.
- Prefer extracting real production seams over stacking mocks.
- When mocking data, mirror the full real structure rather than partial ad hoc
  objects.
- Treat tests as part of implementation, not a later phase.

## Build And Tooling Gotchas

- Use PowerShell wrappers for Flutter and Dart commands.
- Use `pwsh -File tools/build.ps1` for builds instead of raw `flutter build`.
- Do not run `Stop-Process -Name 'dart'`; it can kill unrelated background Dart
  processes.
- On Android API 36, use `db.rawQuery('PRAGMA ...')` instead of `db.execute()`
  for PRAGMA calls.
- Use `tools/start-driver.ps1` and `tools/stop-driver.ps1` for driver-based
  testing.

## File Purpose

- `.claude/CLAUDE.md` is the compact always-on project manual.
- This file is on-demand durable memory only.
