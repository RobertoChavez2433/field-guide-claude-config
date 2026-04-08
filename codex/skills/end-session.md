# Codex Skill: End Session

## Trigger

- `/end-session`
- `end session`

## Goal

Write a compatible handoff so Claude and Codex can both resume from the same
project state.

## Hard Rules

- No git commands. Use conversation context and observed work only.
- Zero user input by default.
- Update only the shared `.claude` handoff/state files that materially changed.
- Keep `_state.md` session entries compressed.
- Do not create or update `.claude/defects/*`; GitHub issues are the defect system of record.

## Primary Files To Update

- `.claude/autoload/_state.md`
- `.claude/state/PROJECT-STATE.json` when project-level status/blockers changed
- `.claude/state/feature-<name>.json` only for features materially touched

## Workflow

1. Gather the session summary from conversation context:
   - main focus
   - completed tasks
   - decisions made
   - next priorities
   - issue-worthy defects discovered
2. Update `.claude/autoload/_state.md` with a compressed session entry:

```markdown
### Session N (YYYY-MM-DD, Codex)
**Work**: Brief 1-line summary
**Decisions**: Key decisions made
**Next**: Top 1-3 priorities
```

3. If `_state.md` holds more than 5 sessions, rotate the oldest session into
   `.claude/logs/state-archive.md`.
4. Update `.claude/state/PROJECT-STATE.json` or touched
   `.claude/state/feature-<name>.json` only if status actually changed.
5. If this session discovered a new unresolved bug, capture the GitHub issue ID
   or filing requirement in `_state.md` or the relevant feature/project state.
6. Present a compact handoff summary:
   - session summary
   - features touched
   - GitHub issues filed or still open
   - next priorities
   - reminder that `resume session` loads the handoff next time

## Shared-State Guarantee

This skill writes the same handoff files Claude expects, so either tool can
resume the next session.

## Upstream Reference

- `.claude/skills/end-session/SKILL.md`
