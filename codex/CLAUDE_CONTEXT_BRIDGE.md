# Claude Context Bridge

This file maps the existing `.claude/` library into targeted, low-noise loads
for Codex. Open only the files needed for the current task.

## Session Handoff

- `.claude/autoload/_state.md`
- `.claude/memory/MEMORY.md`
- `.claude/state/PROJECT-STATE.json`

## Current Work Context

Feature-specific context now lives primarily in active plans, specs, rules, and
repo code. Do not assume the older per-feature docs, implementation guides,
architecture-decision files, or feature-matrix surface still exists.

Prefer:

1. `.codex/PLAN.md`
2. the matching file in `.codex/plans/`
3. the matching file in `.claude/plans/`
4. the matching file in `.claude/specs/`
5. the matching directory in `.claude/tailor/`
6. repo code plus the relevant `.claude/rules/` files

### Sync Shortcut

For sync work, prefer:

1. `.claude/rules/sync/sync-patterns.md`
2. the active sync item in `.codex/plans/`
3. the matching upstream sync plan/spec in `.claude/plans/` or
   `.claude/specs/`
4. repo code under `lib/features/sync/`
5. `.claude/test-flows/` only when verification flow details matter

## Shared Rules

Load by domain, not all at once:

- `.claude/rules/architecture.md`
- `.claude/rules/build-rules.md`
- `.claude/rules/platform-standards.md`
- `.claude/rules/frontend/flutter-ui.md`
- `.claude/rules/frontend/ui-prototyping.md`
- `.claude/rules/backend/data-layer.md`
- `.claude/rules/backend/supabase-sql.md`
- `.claude/rules/auth/supabase-auth.md`
- `.claude/rules/sync/sync-patterns.md`
- `.claude/rules/database/schema-patterns.md`
- `.claude/rules/testing/testing.md`
- `.claude/rules/pdf/pdf-generation.md`
- `.claude/rules/pdf/pdf-extraction-testing.md`

## Agent Files

Use these as routing references:

- `.claude/agents/plan-writer-agent.md`
- `.claude/agents/code-review-agent.md`
- `.claude/agents/security-agent.md`
- `.claude/agents/completeness-review-agent.md`
- `.claude/agents/debug-research-agent.md`

## Skills

Live `.claude` skill entrypoints:

- `resume-session`
- `end-session`
- `brainstorming`
- `tailor`
- `writing-plans`
- `implement`
- `systematic-debugging`
- `test`
- `audit-docs`
- legacy Codex alias only: `audit-config`

Codex-facing wrappers:

- `.codex/skills/resume-session.md`
- `.codex/skills/end-session.md`
- `.codex/skills/brainstorming.md`
- `.codex/skills/tailor.md`
- `.codex/skills/writing-plans.md`
- `.codex/skills/implement.md`
- `.codex/skills/systematic-debugging.md`
- `.codex/skills/test.md`
- `.codex/skills/audit-docs.md`
- `.codex/skills/audit-config.md`

Persona notes live in:

- `.codex/skills/references/codex-agent-personas.md`

## Shared References

- `.claude/CLAUDE.md`
- `.claude/doc-drift-map.json` for audit-only path/reference drift work
- `.claude/outputs/`
- `.claude/test-results/`
- `.claude/code-reviews/`
- `.claude/agent-memory/` only when a matching review persona needs durable
  context

## Permissions Bridge

- `.claude/settings.local.json`
- `.codex/settings.local.json`

Codex does not inherit these automatically in hosted sessions.

## High-Noise Areas

Avoid by default:

- `.claude/logs/*`
- `.claude/plans/completed/*`
- `.claude/backlogged-plans/*`
- `.claude/.git/*`
