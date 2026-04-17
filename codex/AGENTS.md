# Codex Context Layer

This directory is the Codex-facing bridge for the project. It is intentionally
small: use it to find the right context, not to duplicate the entire
`.claude/` knowledge base.

## Default Startup Flow

1. Read this file.
2. Read `.codex/Context Summary.md`.
3. Read `.codex/PLAN.md` and the smallest relevant file in `.codex/plans/`.
4. Use `.codex/CLAUDE_CONTEXT_BRIDGE.md` only when you need specific
   `.claude/` files.

## Operating Rules

- Keep startup context lean.
- Keep `apply_patch` batches small; do not attempt giant multi-file patches in
  one call.
- Treat `.claude/CLAUDE.md` as a project manual, not default startup context.
- For handoff work, prefer `.claude/autoload/_state.md` first, then
  `.claude/memory/MEMORY.md` only if durable patterns matter.
- For active work, prefer `.codex/PLAN.md`, `.codex/plans/`,
  `.claude/plans/`, `.claude/specs/`, and `.claude/tailor/`.
- Load only the matching `.claude/rules/` files for the surface you are
  touching.
- Use `.claude/agents/` as review and routing references, not default startup
  context.

## Live `.claude/` Surface

Use the bridge to load the smallest relevant slice of the current `.claude/`
library:

- session handoff:
  - `.claude/autoload/_state.md`
  - `.claude/memory/MEMORY.md`
  - `.claude/state/PROJECT-STATE.json`
- repo manual:
  - `.claude/CLAUDE.md`
- workflow rules:
  - `.claude/rules/**`
- shared workflows:
  - `.claude/skills/**`
- plans, specs, and tailor output:
  - `.claude/plans/**`
  - `.claude/specs/**`
  - `.claude/tailor/**`
- review personas:
  - `.claude/agents/**`
- test orchestration:
  - `.claude/test-flows/**`
  - `.claude/test-results/**`
- audit-only references:
  - `.claude/doc-drift-map.json`
  - `.claude/outputs/**`

## Planning

- Save new Codex-authored plans to `.codex/plans/`.
- Use `YYYY-MM-DD-<topic>-plan.md`.
- Reference existing `.claude/plans/*.md` work from `.codex/PLAN.md` instead
  of cloning it unless a Codex-specific addendum is needed.

## Testing Non-Negotiables

- Test real behavior, not mock presence or mock-only rendering.
- Do not use `MOCK_AUTH`; verify auth and sync only against real sessions and real backend state.
- UI E2E is a bug-discovery gate: a cell is not passed if screenshots, sync
  state, or debug logs show UI/layout/runtime/sync defects.
- Keep E2E flows concise: seed feature preconditions through `/driver/seed`;
  auth/setup stays in auth flows only.
- Keep S21 primary; prefer `flutter run` hot reload/restart for Dart/UI iteration.
- Prefer `scripts/flutter_run_endpoint.ps1` for S21 `flutter run`; use
  `POST http://127.0.0.1:4950/reload` before restart/rebuild.
- Use the debug/driver server for live S21 automation when available.
- Avoid `flutter clean` unless stale-build evidence requires it.
- Prefer live backend/device testing; Docker Desktop and the local Supabase stack are available as fallback tools when remote checks are risky or credentials are unstable.
- Prefer real production seams over large mock stacks.
- Do not add test-only hooks, methods, or lifecycle APIs to production code.
- Mock only at lower-level boundaries after the real dependency chain and side
  effects are understood.
- If a test is hard to write honestly, extract a real production seam instead
  of inventing a test-only escape hatch.
- Use `TestingKeys`; do not introduce fake test IDs or assert on placeholder
  widgets.

## Permissions

- Claude's local allowlist lives in `.claude/settings.local.json`.
- A Codex-side mirror lives in `.codex/settings.local.json`.
- Codex cannot import either file automatically in hosted sessions.

## Compatibility Skills

Treat these messages as workflow triggers:

- `/resume-session` or `resume session`
- `/end-session` or `end session`
- `/implement <plan>` or `implement <plan>`
- `/writing-plans <spec>` or `writing plans <spec>`
- `/brainstorming` or `brainstorming` or `brainstorm <topic>`
- `/tailor <spec>` or `tailor <spec>`
- `/systematic-debugging` or `systematic debugging` or `systematic debug <issue>`
- `/test ...` or `test ...`
- `/audit-docs` or `audit docs`
- legacy alias: `/audit-config` or `audit config`

Workflow definitions live in:

- `.codex/skills/resume-session.md`
- `.codex/skills/end-session.md`
- `.codex/skills/implement.md`
- `.codex/skills/writing-plans.md`
- `.codex/skills/brainstorming.md`
- `.codex/skills/tailor.md`
- `.codex/skills/systematic-debugging.md`
- `.codex/skills/test.md`
- `.codex/skills/audit-docs.md`
- `.codex/skills/audit-config.md`

These wrappers are Codex-facing, but they intentionally target the same
shared `.claude` rules, skills, specs, and handoff files.

## Avoid By Default

- `.claude/logs/*`
- `.claude/plans/completed/*`
- `.claude/backlogged-plans/*`
- `.claude/.git/*`
