# Codex Skill: Resume Session

## Trigger

- `/resume-session`
- `resume session`

## Goal

Load the same hot handoff Claude uses and return control quickly, without
pulling in extra feature context or running git commands.

## Hard Rules

- No git commands.
- No questions.
- No pre-loading of feature docs, rules, or constraints.
- Read only the hot handoff files unless the user asks for more after resume.

## Files To Read

1. `.claude/memory/MEMORY.md`
2. `.claude/autoload/_state.md`

## Do Not Auto-Load

- `.claude/logs/*`
- `.claude/plans/completed/*`
- feature docs, constraints, rules, or state JSON files unless the user
  immediately asks for them

## Output Shape

Return only:

- current phase
- current status
- one-line summary of the most recent session
- top next tasks

Use this compact structure:

```text
**Phase**: ...
**Status**: ...
**Last Session**: ...

**Next Tasks**:
1. ...
2. ...
3. ...

Ready - what are we working on?
```

Then stop and wait for the user's actual task.

## Shared-State Guarantee

This skill reads the exact same `.claude` handoff files Claude uses, so both
tools resume from the same state snapshot.

## Upstream Reference

- `.claude/skills/resume-session/SKILL.md`
