# Codex Skill: Test

## Trigger

- `/test ...`
- `test ...`

## Goal

Run the shared HTTP-driver testing workflow through the canonical testing
surface without inventing wave agents or fixer agents.

## Canonical Families

- `ui-flow`: navigation, route/sentinel, screenshot, visible-layout, auth/routing, form fidelity, preview, and export checks.
- `sync-flow`: real UI mutation plus UI-triggered sync against live Supabase, including multi-device contention and concurrency stress.
- `Live Soak`: prolonged overlapped backend/headless/device testing.
- `Local Driver`: deterministic driver or launcher drills and endpoint checks.

## Output Root

- `tools/testing/test-results/YYYY-MM-DD/<run-id>/`
- PDF extraction replay audits must write compact outputs under
  `tools/testing/test-results/YYYY-MM-DD/pdf-extraction-replay-audit-<time>-<run_id>/`
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
2. map the request to `ui-flow`, `sync-flow`, `Live Soak`, or `Local Driver`
3. run driver preflight when the chosen family needs it
4. load the required testing docs
5. execute flows in order
6. write artifacts under `tools/testing/test-results/`
6. summarize failures in chat

## Shared References

- `.claude/skills/test/SKILL.md`
- `.claude/test-flows/flow-dependencies.md`
- `.claude/test-flows/sync/framework.md`
- `tools/testing/docs/testing-glossary.md`
- `tools/testing/docs/flow-selection-guide.md`

## Notes

- use `tools/start-driver.ps1` and `tools/stop-driver.ps1`
- save screenshots for every UI cell, but manually inspect only failures,
  warnings, and small feature/device samples
- "stress test sync" maps to `sync-flow`
- navigation/layout requests map to `ui-flow`
- "run prerelease verification", "run pre-update verification", and
  "final verification before merge" map to
  `tools/testing/Invoke-PreUpdateVerification.ps1`
- prerelease device scope is caller-selected per run; phone, tablet,
  emulator, and mixed actor sets are all valid
