# Codex Skill: Implement

## Trigger

- `/implement <plan>`
- `implement <plan>`

## Goal

Execute a shared `.claude/plans/...` plan phase-by-phase using Codex-compatible
personas, checkpoints, validation, and review gates.

## Plan Sources

- Prefer active plans in `.claude/plans/`
- Use `YYYY-MM-DD-<topic>-codex-plan.md` for Codex-authored plans in that same
  directory

## Workflow

1. Accept the requested shared plan path.
2. Read the plan and extract the phases before changing code.
3. Check for a checkpoint at `.claude/state/implement-codex-checkpoint.json`.
4. Present the phase list and wait for user confirmation before starting.
5. Execute one phase at a time:
   - load only the needed feature context
   - route work by internal persona
   - make the changes
   - run validation
   - run completeness, code-review, and security-review passes
   - update the checkpoint
6. After all phases pass, run final integration gates.
7. Present a completion summary. Do not commit or push.

## Internal Personas

Use the same agent names Claude uses, but as Codex internal modes:

- `frontend-flutter-specialist-agent`
- `backend-data-layer-agent`
- `backend-supabase-agent`
- `auth-agent`
- `pdf-agent`
- `code-review-agent`
- `security-agent`
- `qa-testing-agent`

Routing and persona notes live in:

- `.codex/skills/references/codex-agent-personas.md`

## Checkpoint File

Use the shared state directory, but tag the checkpoint for Codex:

- `.claude/state/implement-codex-checkpoint.json`

Track:

- plan path
- per-phase status
- per-phase review results
- modified files
- integration-gate status
- decisions and blockers

## Validation Gates

After each phase:

- run targeted checks required by the phase
- prefer `pwsh -Command "flutter analyze"` and relevant focused tests
- if the phase changes broad shared behavior, run wider tests before advancing

Before final completion:

- `pwsh -Command "flutter analyze"`
- `pwsh -Command "flutter test"`
- broader build/test command only if the plan or touched surface requires it

## Review Passes

For each phase, run three internal review passes after validation:

1. Completeness review:
   - verify the phase matches the plan exactly
   - verify tests requested by the plan actually exist
   - verify wiring is real, not just code presence
2. `code-review-agent` persona:
   - architecture, maintainability, duplication, performance
3. `security-agent` persona:
   - auth, data exposure, validation boundaries, tenant/RLS concerns

Fix all material findings before advancing the phase. If blocked after repeated
attempts, stop and present the blocker to the user.

## Shared-State Convention

If the implementation materially changes active work status, reflect that in
the same `.claude` handoff files during `end session` so Claude sees the same
current state.

## Routing References

- `.claude/state/AGENT-FEATURE-MAPPING.json`
- `.claude/agents/*.md`
- `.codex/skills/references/codex-agent-personas.md`

These are routing references. Codex implements the work itself, but it should
follow the same ownership boundaries, review personas, and context-loading
patterns.

## Upstream Reference

- `.claude/skills/implement/SKILL.md`
