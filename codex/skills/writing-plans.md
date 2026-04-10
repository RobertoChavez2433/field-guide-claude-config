# Codex Skill: Writing Plans

## Trigger

- `/writing-plans <spec>`
- `writing plans <spec>`

## Goal

Turn an approved spec plus tailor output into a Codex-authored implementation
plan.

## Output

Write new Codex plans to:

- `.codex/plans/YYYY-MM-DD-<topic>-plan.md`

Reference existing `.claude/plans/*.md` when you are extending or aligning with
shared Claude-authored work.

## Workflow

1. read the approved spec from `.claude/specs/`
2. find the matching tailor directory under `.claude/tailor/`
3. write the plan with a machine-readable phase-range block
4. run the same review trio Claude uses
5. fix material findings
6. present the saved plan path and summary

## Live Review References

- `.claude/agents/completeness-review-agent.md`
- `.claude/agents/code-review-agent.md`
- `.claude/agents/security-agent.md`

## Upstream Reference

- `.claude/skills/writing-plans/SKILL.md`
