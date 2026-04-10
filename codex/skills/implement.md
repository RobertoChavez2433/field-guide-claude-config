# Codex Skill: Implement

## Trigger

- `/implement <plan>`
- `implement <plan>`

## Goal

Execute a plan phase-by-phase using generic implementation workers plus the live
review agents.

## Plan Sources

- prefer `.codex/plans/` for Codex-authored plans
- accept shared `.claude/plans/` when continuing Claude-authored work

## Core Rules

- keep the orchestrator thin
- implementers and fixers are generic Sonnet workers
- reviewers use the live Claude review agents
- do not invent specialist agents that no longer exist

## Workflow

1. resolve the plan path
2. read only the plan header and phase structure first
3. confirm the phase list with the user
4. execute one phase at a time
5. run completeness, code-review, and security review after each phase
6. fix material findings before advancing
7. run one final review sweep before closing

## Live Review References

- `.claude/agents/completeness-review-agent.md`
- `.claude/agents/code-review-agent.md`
- `.claude/agents/security-agent.md`

## Upstream Reference

- `.claude/skills/implement/SKILL.md`
