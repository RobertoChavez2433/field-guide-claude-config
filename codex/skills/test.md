# Codex Skill: Test

## Trigger

- `/test ...`
- `test ...`

## Goal

Run the same ADB-centered test workflow Claude uses, while keeping Codex
compatible with environments that may not support background wave agents.

## Core Rules

- Keep the orchestrator thin.
- Store detailed output on disk first.
- Read flow reports from disk only when the user asks to inspect a failure.
- Check runtime/device prerequisites before launching flows.

## Output Location

Write results to:

- `.claude/test-results/YYYY-MM-DD_HHmm_codex_<descriptor>/`

Keep the same subdirectories Claude uses:

- `screenshots/`
- `logs/`
- `flows/`

## Workflow

1. Parse flags or named flows.
2. Resolve flow dependencies and execution order.
3. Run pre-flight:
   - device check
   - build/install check
     - prefer `tools/start-driver.ps1`, which now reuses a current Android
       driver build and only rebuilds/reinstalls when inputs changed
     - use `-ForceRebuild` only when you suspect the cached driver artifact is
       wrong
   - app launch
   - run directory creation
4. Execute flows in dependency order:
   - use parallel waves only when the environment supports safe parallelism
   - otherwise run the same waves sequentially while preserving the same output
     format
5. Write per-flow reports and logs to disk.
6. Summarize pass/fail/skip counts in chat.
7. Read specific flow reports only on demand.

## Sync Verification Coverage

When the requested test scope includes sync verification, treat the shared registry
and sync flow docs as the source of truth:

- `.claude/test-flows/flow-dependencies.md`
- `.claude/test-flows/sync/framework.md`
- `.claude/test-flows/sync/flows-S01-S03.md`
- `.claude/test-flows/sync/flows-S04-S06.md`
- `.claude/test-flows/sync/flows-S07-S10.md`
- `.claude/test-flows/sync/flows-S11-S19.md`

The current sync verification range is `S01-S21`, including:

- core data round-trips
- SQLite row verification
- `change_log` drain verification
- Supabase row verification
- storage object verification for file-backed tables
- sync-mode coverage for quick resume, realtime hints, background FCM recovery,
  global full sync UI, dirty-scope isolation, maintenance housekeeping, and
  private-channel registration / teardown verification
- user-scoped sync coverage for support tickets and consent audit records

## Pay App / Export Coverage

When the requested scope touches pay applications or exported-history behavior,
include:

- `.claude/test-flows/tiers/toolbox-and-pdf.md`
- `.claude/test-flows/tiers/pay-app-and-exports.md`

Required pay-app/export checks:

- exported-artifact history visibility
- exact-range replace with pay-app number preservation
- overlap-block behavior
- pay-app delete propagation
- contractor comparison import plus discrepancy PDF export
- saved pay-app artifact sync/delete verification

## Shared-State Guarantee

This skill writes test artifacts into the same `.claude/test-results/`
structure Claude uses, so results stay shared across tools.

## Upstream Reference

- `.claude/skills/test/SKILL.md`
- `.claude/agents/test-wave-agent.md`
