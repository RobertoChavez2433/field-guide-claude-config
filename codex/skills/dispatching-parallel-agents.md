# Codex Skill: Dispatching Parallel Agents

## Goal

Mirror Claude's parallel-dispatch workflow as a Codex internal pattern for
non-overlapping research, implementation, or review work.

## Core Rules

- Use only when the work can be split cleanly.
- Keep max parallel wave size at 3.
- Prefer read-only parallelism for research and review.
- If files overlap or ordering matters, fall back to sequential execution.

## Workflow

1. Split work by file ownership or task domain.
2. Confirm the tasks are non-overlapping.
3. Dispatch at most 3 parallel lanes.
4. Merge results into one summary.
5. Run an integration review before declaring completion.

## Shared References

- `.claude/state/AGENT-CHECKLIST.json`
- `.claude/state/AGENT-FEATURE-MAPPING.json`
- `.codex/skills/references/codex-agent-personas.md`

## Usage

- planning research
- phase-local implementation on disjoint files
- review passes across different concerns

This is an internal Codex workflow pattern, not a user-facing slash command by
default.
