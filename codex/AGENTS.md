# Codex Context Layer

This directory is the Codex-facing bridge for the project. It is intentionally
small: use it to find the right context, not to duplicate the entire
`.claude/` knowledge base.

## Default Startup Flow

1. Read this file.
2. Read `.codex/Context Summary.md`.
3. Read `.codex/PLAN.md`.
4. Use `.codex/CLAUDE_CONTEXT_BRIDGE.md` only when you need specific
   `.claude/` files.

## Operating Rules

- Keep startup context lean.
- Keep `apply_patch` batches small; do not attempt giant multi-file patches in
  one call.
- Treat `.claude/CLAUDE.md` as a project manual, not default startup context.
- For feature work, load only the matching feature state, docs, and
  constraints.
- For handoff work, prefer `.claude/autoload/_state.md` first, then
  `.claude/memory/MEMORY.md` only if durable patterns matter.

## Planning

- Save new Codex-authored plans to `.codex/plans/`.
- Use `YYYY-MM-DD-<topic>-plan.md`.
- Reference existing `.claude/plans/*.md` work from `.codex/PLAN.md` instead
  of cloning it unless a Codex-specific addendum is needed.

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

These wrappers are Codex-facing, but they intentionally target the same
shared `.claude` rules, skills, specs, and handoff files.

## Avoid By Default

- `.claude/logs/*`
- `.claude/plans/completed/*`
- `.claude/.git/*`
