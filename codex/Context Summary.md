# Context Summary

## Project Snapshot

- App: Field Guide (`construction_inspector`) for construction inspectors
- Stack: Flutter, Provider, SQLite-first local storage, optional Supabase sync,
  Firebase on mobile
- Shape: `lib/core`, `lib/features`, `lib/services`, `lib/shared`,
  `lib/test_harness`

## Core Entry Points

- `lib/main.dart` wires startup, providers, database, auth, sync, and services.
- `lib/core/router/app_router.dart` owns route guards, onboarding redirects,
  password recovery trapping, and shell navigation.
- `lib/core/database/database_service.dart` owns SQLite schema creation and
  migrations.

## Current Active Context

- Latest session handoff source: `.claude/autoload/_state.md`
- Durable project patterns: `.claude/memory/MEMORY.md`
- Highest-priority active plan: `.claude/plans/2026-02-28-password-reset-token-hash-fix.md`
- Major open secondary plan: `.claude/plans/2026-02-22-testing-strategy-overhaul.md`

## Use This Directory To Stay Lean

- `.codex/PLAN.md` indexes active planning without loading all historical plans.
- `.codex/CLAUDE_CONTEXT_BRIDGE.md` maps the exact `.claude/` files to open for
  session handoff, feature context, agents, skills, and rules.
