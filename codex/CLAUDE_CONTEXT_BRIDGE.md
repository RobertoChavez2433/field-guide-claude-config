# Claude Context Bridge

This file maps the existing `.claude/` library into targeted, low-noise loads
for Codex. Open only the files needed for the current task.

## Session Handoff

- `.claude/autoload/_state.md`
- `.claude/memory/MEMORY.md`
- `.claude/state/PROJECT-STATE.json`
- `.claude/state/FEATURE-MATRIX.json`

## Feature Context

For a feature `<name>`, prefer:

1. `.claude/state/feature-<name>.json`
2. `.claude/architecture-decisions/<name>-constraints.md`
3. `.claude/docs/features/feature-<name>-overview.md`
4. `.claude/docs/features/feature-<name>-architecture.md`
5. optional active plan/spec or GitHub issue context only if needed

### Sync Shortcut

For sync work, prefer:

1. `.claude/docs/features/feature-sync-overview.md`
2. `.claude/docs/features/feature-sync-architecture.md`
3. `.claude/docs/guides/implementation/sync-architecture.md`
4. `.claude/rules/sync/sync-patterns.md`
5. active sync plan/spec only if needed

## Shared Rules

Load by domain, not all at once:

- `.claude/rules/architecture.md`
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

Persona notes live in:

- `.codex/skills/references/codex-agent-personas.md`

## Documentation Layers

- `.claude/docs/INDEX.md`
- `.claude/docs/features/`
- `.claude/docs/guides/`
- `.claude/architecture-decisions/`
- `.claude/prds/`
- `.claude/test-results/`
- `.claude/code-reviews/`

## Permissions Bridge

- `.claude/settings.local.json`
- `.codex/settings.local.json`

Codex does not inherit these automatically in hosted sessions.

## High-Noise Areas

Avoid by default:

- `.claude/logs/*`
- `.claude/plans/completed/*`
- `.claude/.git/*`
