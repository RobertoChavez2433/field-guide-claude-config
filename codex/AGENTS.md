# Codex Context Layer

This directory is the Codex-facing bridge for the project. It is intentionally
small: use it to find the right context, not to duplicate the entire
`.claude/` knowledge base.

## Default Startup Flow

1. Read this file.
2. Read `.codex/Context Summary.md`.
3. Read `.codex/PLAN.md`.
4. Use `.codex/CLAUDE_CONTEXT_BRIDGE.md` only when you need to open specific
   `.claude/` files.

## Operating Rules

- Keep startup context lean. Do not preload broad `.claude/` docs unless the
  task clearly needs them.
- Treat `.claude/CLAUDE.md` as a broad project manual. Load it only for
  cross-cutting work, build/test command reference, or when no narrower file
  applies.
- For feature work, load only the matching feature state, docs, constraints,
  and any relevant GitHub issue context.
- For session handoff, prefer `.claude/autoload/_state.md` first, then
  `.claude/memory/MEMORY.md` only if durable patterns matter to the task.

## Planning

- Save new Codex-authored plans to `.claude/plans/`.
- Tag Codex-authored artifacts in shared `.claude` directories with
  `-codex-<type>`, for example:
  `YYYY-MM-DD-<topic>-codex-plan.md`.
- Keep Codex plans short and reference existing `.claude/plans/*.md` files
  instead of cloning their full contents when extending earlier work.

## Permissions

- Claude's local allowlist lives in `.claude/settings.local.json`.
- A Codex-side mirror now lives in `.codex/settings.local.json`.
- Codex cannot import either file automatically in hosted sessions.
- For Codex sessions that need write/build/test work, prefer requesting a
  single early runtime approval for `pwsh -Command` rather than many narrow
  approvals.

## Compatibility Skills

Codex does not have Claude's native slash-command registry, so this repo uses
documented compatibility aliases instead.

Treat these messages as workflow triggers:

- `/resume-session` or `resume session`
- `/end-session` or `end session`
- `/implement <plan>` or `implement <plan>`
- `/writing-plans <spec>` or `writing plans <spec>`
- `/brainstorming` or `brainstorming` or `brainstorm <topic>`
- `/systematic-debugging` or `systematic debugging` or `systematic debug <issue>`
- `/test ...` or `test ...`
- `/audit-config` or `audit config`

Workflow definitions live in:

- `.codex/skills/resume-session.md`
- `.codex/skills/end-session.md`
- `.codex/skills/implement.md`
- `.codex/skills/writing-plans.md`
- `.codex/skills/brainstorming.md`
- `.codex/skills/systematic-debugging.md`
- `.codex/skills/test.md`
- `.codex/skills/audit-config.md`

These wrappers are Codex-facing, but they intentionally update the same
`.claude` handoff/state files so both tools share the same project memory.

Codex-authored specs, plans, reviews, and checkpoints should live in the same
`.claude` directories Claude uses, with `codex` in the artifact name so the
authoring tool remains visible without splitting the workflow.

## Avoid By Default

- `.claude/logs/*`
- `.claude/plans/completed/*`
- `.claude/.git/*`
