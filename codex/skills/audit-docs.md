# Codex Skill: Audit Docs

## Trigger

- `/audit-docs`
- `audit docs`

## Goal

Audit the live `.claude/` and `.codex/` workflow surface, report drift, and
optionally refresh `.claude/doc-drift-map.json`.

## Workflow

1. prefer CodeMunch for the live surface audit
2. validate live path and symbol references
3. check rules, skills, agents, memory, and wrappers for cohesion
4. write the report to `.claude/outputs/`
5. refresh `.claude/doc-drift-map.json` only when requested or clearly stale

## Scope

- live `.claude/` files
- `.codex/` bridge files
- not historical archives unless the user asks

## Upstream Reference

- `.claude/skills/audit-docs/SKILL.md`
