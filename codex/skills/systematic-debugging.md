# Codex Skill: Systematic Debugging

## Trigger

- `/systematic-debugging`
- `systematic debugging`
- `systematic debug <issue>`

## Goal

Debug with the same root-cause-first discipline Claude uses, but through the
Codex environment.

## Core Rules

- no fixes before root cause
- stay interactive
- do not write code without explicit approval
- use background research only for read-only help

## Workflow

1. choose Quick or Deep mode
2. triage the issue and identify the smallest likely code path
3. inspect coverage and add instrumentation only where needed
4. reproduce and gather evidence
5. present a root cause report
6. stop for approval before implementing any fix

## Live Support References

- `.claude/agents/debug-research-agent.md`
- `.claude/skills/systematic-debugging/SKILL.md`
