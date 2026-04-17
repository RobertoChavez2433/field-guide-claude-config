# Codex Skill: Test

## Trigger

- `/test ...`
- `test ...`

## Goal

Run the shared HTTP-driver test workflow and write artifacts to the shared
test-results root without inventing wave agents or fixer agents.

## Output Root

- `.claude/test-results/YYYY-MM-DD_HHmm_codex_<descriptor>/`
- PDF extraction replay audits must write compact outputs under
  `.claude/test-results/YYYY-MM-DD/pdf-extraction-replay-audit-<time>-<run_id>/`
  by running `scripts/audit_pdf_extraction_replay.ps1`.

## Core Rules

- follow the shared driver and tier docs
- use the same sync proof standard Claude uses
- do not auto-fix failures
- do not reference deleted test agents
- test real behavior, not mock presence or placeholder rendering
- prefer real production seams over large mock stacks
- do not add test-only hooks, methods, or lifecycle APIs to production code
- mock only at lower-level boundaries after the real dependency chain is understood
- if a test is hard to write honestly, extract a real production seam instead of
  inventing a test-only escape hatch
- use `TestingKeys`; do not rely on fake test IDs
- UI E2E cells fail on visible UI defects, sync defects, or new debug-log
  errors; route/key assertions alone are not enough
- keep feature flows concise: use seeded preconditions instead of replaying
  auth/setup through downstream features
- for PDF extraction replay review, use compact failure CSVs and the audit
  script; do not broad-load huge replay JSON files with PowerShell or rely on
  truncated console/JSON dumps

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
- save screenshots for every UI cell, but manually inspect only failures,
  warnings, and small feature/device samples
- keep artifacts shared so either tool can resume the run
