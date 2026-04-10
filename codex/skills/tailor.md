# Codex Skill: Tailor

## Trigger

- `/tailor <spec>`
- `tailor <spec>`

## Goal

Build a focused implementation-context package from an approved spec and save it
under `.claude/tailor/`.

## Workflow

1. read the approved spec from `.claude/specs/`
2. use CodeMunch to map touched files, key symbols, dependencies, and blast
   radius
3. verify ground-truth literals and paths
4. write the tailor directory
5. stop and hand off to `/writing-plans`

## Output Root

- `.claude/tailor/YYYY-MM-DD-<spec-slug>/`

## Upstream Reference

- `.claude/skills/tailor/SKILL.md`
