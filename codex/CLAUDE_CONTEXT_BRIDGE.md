# Claude Context Bridge

This file maps the existing `.claude/` library into targeted, low-noise loads
for Codex. Use it as an index. Open only the files needed for the current task.

## Session Handoff

Use these when you need current status or to resume where a prior session left
off:

- `.claude/autoload/_state.md`: Current phase, recent sessions, next actions
- `.claude/memory/MEMORY.md`: Durable patterns, pitfalls, and recurring
  implementation guidance
- `.claude/state/PROJECT-STATE.json`: Project-wide blockers and status
- `.claude/state/FEATURE-MATRIX.json`: Cross-feature status overview

## Feature Context (Load Only For The Touched Feature)

For a feature `<name>`, the canonical context chain is:

1. `.claude/state/feature-<name>.json`
2. `.claude/architecture-decisions/<name>-constraints.md`
3. `.claude/docs/features/feature-<name>-overview.md`
4. `.claude/docs/features/feature-<name>-architecture.md`
5. Optional: matching `.claude/prds/*`, active `.claude/plans/*`, or GitHub issue context

### Sync-Specific Shortcut

For sync work, prefer this targeted chain before broad browsing:

1. `.claude/docs/features/feature-sync-overview.md`
2. `.claude/docs/features/feature-sync-architecture.md`
3. `.claude/docs/guides/implementation/sync-architecture.md`
4. `.claude/rules/sync/sync-patterns.md`
5. Active sync plan/spec under `.claude/plans/` and `.claude/specs/`

## Shared Rules And Cross-Cutting References

Load these by domain, not all at once:

- Architecture baseline: `.claude/rules/architecture.md`
- Platform/build constraints: `.claude/rules/platform-standards.md`
- Shared validation rules: `.claude/architecture-decisions/data-validation-rules.md`
- UI work: `.claude/rules/frontend/flutter-ui.md`
- UI prototyping: `.claude/rules/frontend/ui-prototyping.md`
- Data layer: `.claude/rules/backend/data-layer.md`
- Supabase/schema: `.claude/rules/backend/supabase-sql.md`
- Auth: `.claude/rules/auth/supabase-auth.md`
- Sync: `.claude/rules/sync/sync-patterns.md`
- Database schema: `.claude/rules/database/schema-patterns.md`
- Testing: `.claude/rules/testing/testing.md`
- PDF: `.claude/rules/pdf/pdf-generation.md`
- Shared analyzer abstractions: `.claude/docs/guides/implementation/shared-analyzer-safe-patterns.md`

## Agent Files (Claude Subagent Definitions)

These are useful as routing/reference docs even when Codex is doing the work
itself:

- PLAN/PLAN FRAGMENTS: `.claude/agents/plan-writer-agent.md`
- REVIEW: `.claude/agents/code-review-agent.md`,
  `.claude/agents/security-agent.md`,
  `.claude/agents/completeness-review-agent.md`
- DEBUG RESEARCH: `.claude/agents/debug-research-agent.md`

## Skills And How Claude Uses Them

Claude skill definitions live in `.claude/skills/*/SKILL.md`.

### User-invocable skills

- `resume-session`
- `end-session`
- `implement`
- `writing-plans`
- `brainstorming`
- `systematic-debugging`
- `test`
- `audit-config`
- `dispatching-parallel-agents` (workflow pattern / internal Codex wrapper)

Codex does not auto-run these skills. Use the relevant `SKILL.md` file as a
targeted workflow reference when the task matches.

Codex-facing wrappers for the shared workflows live in:

- `.codex/skills/resume-session.md`
- `.codex/skills/end-session.md`
- `.codex/skills/implement.md`
- `.codex/skills/writing-plans.md`
- `.codex/skills/brainstorming.md`
- `.codex/skills/systematic-debugging.md`
- `.codex/skills/test.md`
- `.codex/skills/audit-config.md`
- `.codex/skills/dispatching-parallel-agents.md`

Those wrappers are the preferred reference for Codex behavior because they are
adapted to this environment while still targeting the same `.claude` files.

Codex uses the live agent files as routing references for review, planning, and
debug research. Implementation itself is handled by generic workers plus the
shared rules and skills.

Persona mapping and usage notes live in:

- `.codex/skills/references/codex-agent-personas.md`

Codex-authored artifacts should stay in the same `.claude` directories as
Claude-authored ones, but include `-codex-` in the filename.

## Documentation Layers

- `.claude/docs/INDEX.md`: Docs map
- `.claude/docs/features/`: Feature overviews and architecture
- `.claude/docs/guides/`: Testing and implementation guides
- `.claude/architecture-decisions/`: Hard constraints by feature/domain
- `.claude/prds/`: Product requirements
- `.claude/test-results/`: Prior test findings
- `.claude/code-reviews/`: Review reports

GitHub issues are the defect system of record. Do not create or update
`.claude/defects/*`.

## Permissions Bridge

- Claude's project-local permission allowlist lives in
  `.claude/settings.local.json`.
- A mirrored copy for Codex-facing project context lives in
  `.codex/settings.local.json`.
- It currently grants broad `Bash(...)`, `WebFetch(...)`, `Write`, and `Edit`
  access for Claude.
- Path-specific entries must match the current repo root:
  `C:\Users\rseba\Projects\Field_Guide_App`.
- Codex cannot inherit either file automatically; runtime approvals still
  depend on the active Codex environment.

## High-Noise / Archive Areas

Do not load these unless a task explicitly needs historical archaeology:

- `.claude/logs/*`
- `.claude/plans/completed/*`
- `.claude/autoload/_state.md` only when session handoff/current status is
  relevant
- `.claude/.git/*`
