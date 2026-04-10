---
name: audit-docs
description: "Audits the live .claude and .codex workflow surface against the current repo, then writes a drift report and optional mapping refresh."
user-invocable: true
disable-model-invocation: true
---

# Audit Docs

Audit the live `.claude/` and `.codex/` workflow surface against the current
repo. This replaces the older `/audit-config` name.

## Goals

- find broken paths and renamed files
- find stale agent, skill, and wrapper references
- check live workflow cohesion
- verify security-critical prompts and rules still exist
- optionally refresh `.claude/doc-drift-map.json`

## Modes

- default: full live-surface audit
- `--regen-map`: refresh `.claude/doc-drift-map.json` only

## Scope

Primary targets:

- `.claude/CLAUDE.md`
- `.claude/rules/`
- `.claude/skills/`
- `.claude/agents/`
- `.claude/memory/`
- `.codex/`

Treat historical directories as out of scope unless the user explicitly asks:

- `logs/`
- `code-reviews/`
- `adversarial_reviews/`
- `plans/completed/`
- `backlogged-plans/`
- historical test artifact directories

## Workflow

1. Refresh or verify the CodeMunch index.
2. Scan the live workflow files for explicit path references.
3. Validate referenced files and symbols against disk and the indexed repo.
4. Check live routing consistency across rules, skills, agents, memory, and
   Codex wrappers.
5. Check the security-critical invariants.
6. Write the report.
7. If requested, regenerate `.claude/doc-drift-map.json`.

## Security-Critical Invariants

Never auto-fix these. Report them only.

- `security-agent.md` remains report-only and read-only in spirit
- `CLAUDE.md` still carries the security non-negotiable
- auth and sync rules still retain their key sentinels
- no workflow silently weakens security boundaries to reduce friction

## Auto-Fix Policy

Without explicit user approval, this skill may only auto-fix:

- broken file paths
- renamed skill or rule filenames
- stale wrapper references
- stale mapping entries in `.claude/doc-drift-map.json`

It must not rewrite architectural policy, security rules, or feature docs on
its own.

## Outputs

Write:

- report: `.claude/outputs/audit-docs-report-YYYY-MM-DD.md`
- optional map refresh: `.claude/doc-drift-map.json`

## Report Shape

The report should include:

- summary counts
- broken paths
- stale references
- live cohesion gaps
- security invariant results
- recommended fix order

## Naming

Prefer `/audit-docs`. Treat `/audit-config` as a legacy alias only if it still
appears in older wrappers or habits.
