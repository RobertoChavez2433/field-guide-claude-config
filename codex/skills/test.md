# Codex Skill: Test

## Trigger

- `/test ...`
- `test ...`

## Goal

Run the shared HTTP-driver test workflow and write artifacts to the shared
test-results root without inventing wave agents or fixer agents.

## Output Root

- `.claude/test-results/YYYY-MM-DD_HHmm_codex_<descriptor>/`

## Core Rules

- follow the shared driver and tier docs
- use the same sync proof standard Claude uses
- do not auto-fix failures
- do not reference deleted test agents

## Workflow

1. resolve the requested scope
2. run driver preflight
3. load the required tier or sync docs
4. execute flows in order
5. write checkpoint and report artifacts under `.claude/test-results/`
6. summarize failures in chat

## Shared References

- `.claude/skills/test/SKILL.md`
- `.claude/test-flows/flow-dependencies.md`
- `.claude/test-flows/sync/framework.md`

## Notes

- use `tools/start-driver.ps1` and `tools/stop-driver.ps1`
- inspect screenshots only when a real failure signal appears
- keep artifacts shared so either tool can resume the run
