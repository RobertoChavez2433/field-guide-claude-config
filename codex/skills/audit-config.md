# Codex Skill: Audit Config

## Trigger

- `/audit-config`
- `audit config`

## Goal

Audit the shared `.claude/` configuration library against the live codebase and
surface broken references, stale mappings, and security invariant failures.

## Hard Rules

- Read-only workflow.
- Do not modify config files automatically.
- Report findings first; only fix after explicit user approval.

## Workflow

1. Index the codebase:
   - prefer CodeMunch if available
   - otherwise use repo search and targeted reads
2. Scan `.claude/` for file and class references.
3. Validate paths against disk.
4. Validate class and symbol references against the codebase.
5. Check security invariants and agent/tool restrictions.
6. Save a structured report to `.claude/outputs/audit-report-YYYY-MM-DD-codex.md`.
7. Present findings and ask whether to fix, defer, or leave manual.

## Scope

Primary target:

- `.claude/`

Optional secondary target when relevant:

- `.codex/` bridge drift versus `.claude/`

## Shared-State Guarantee

This skill audits the same shared configuration library Claude relies on, so
the resulting report applies to both tools.

## Upstream Reference

- `.claude/skills/audit-config/SKILL.md`
