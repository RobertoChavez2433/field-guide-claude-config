# Codex Skill: Brainstorming

## Trigger

- `/brainstorming`
- `brainstorming`
- `brainstorm <topic>`

## Goal

Turn an idea into an approved spec before planning or implementation when the
work is large, ambiguous, or cross-cutting.

## Core Rules

- ask one question at a time
- prefer multiple choice when practical
- ground questions in actual repo context
- do not turn this into a wall-of-text intake form
- small, clear changes may skip brainstorming

## Workflow

1. explore the smallest relevant context
2. classify the work type
3. lock Intent, Scope, and Vision through short gates
4. present 2 to 3 options with a recommendation
5. write the approved spec to `.claude/specs/YYYY-MM-DD-<topic>-codex-spec.md`
6. run self-review and user review
7. hand off to `/tailor` when deeper implementation mapping is needed

## Reference Aids

- `.codex/skills/references/brainstorming-question-patterns.md`
- `.codex/skills/references/brainstorming-design-sections.md`

## Upstream Reference

- `.claude/skills/brainstorming/SKILL.md`
