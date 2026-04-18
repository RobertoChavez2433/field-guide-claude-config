# Sync Soak Unified Implementation Log

Date: 2026-04-18
Status: append-only active log
Controlling checklist:
`.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`

## How To Use This Log

Append one entry per implementation or verification slice. Each entry should
record:

- what changed;
- why it changed;
- exact tests or live gates run;
- artifact paths;
- what stayed open;
- which checklist items were checked off.

Do not treat code changes as complete without artifact-backed evidence when the
checklist requires live device, storage, sync, role, or scale proof.

## 2026-04-18 - Unified Todo Created

Inputs reviewed:

- `.claude/codex/plans/2026-04-18-mdot-1126-typed-signature-sync-soak-plan.md`
- `.claude/codex/plans/2026-04-18-sync-engine-external-hardening-todo.md`
- `.claude/codex/plans/2026-04-18-sync-soak-spec-audit-agent-task-list.md`
- `.claude/codex/reports/2026-04-18-all-test-results-result-index.json`
- `.claude/codex/reports/2026-04-18-enterprise-sync-soak-result-index.json`

Branch audit:

- Current branch: `gocr-integration`.
- Current HEAD: `022a673a`.
- Recent direction: modular sync-soak harness, strict driver failures,
  signature contract repair, S21 form-flow expansion, cleanup replay,
  result-index preservation, and custom lint guardrails.

Agent/result synthesis:

- Full test index: 165 runs, 76 pass, 89 fail.
- Enterprise sync-soak index: 55 runs, 15 pass, 40 fail.
- Current blocker: MDOT 1174R is implemented/wired but not accepted.
- Latest critical run:
  `20260418-s21-mdot1174r-after-ensure-visible-scroll`.
- Latest critical failure: `runtime_log_error`, duplicate `GlobalKey`,
  detached render object assertions, `runtimeErrors=27`, queue residue.
- Recovery proof exists through
  `20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only`, but recovery
  is not mutation acceptance.

Decision recorded:

- PowerSync is a hardening reference, not a migration target for this release.
- Reuse compatible open-source packages/tooling where possible.
- Treat source-available PowerSync Service/CLI internals as design references
  unless licensing is explicitly cleared.
- Jepsen/Elle-style history, generator, nemesis, and checker patterns should
  shape scale testing; use their tooling directly if practical before building
  custom equivalents.
- Reuse discovery must be practical and dismissible: if a candidate does not
  fit licensing, Flutter/Dart/PowerShell harness constraints, Supabase/RLS
  semantics, or real-device evidence, close it as not worth pursuing.

Files changed:

- Added `.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`.
- Added `.codex/checkpoints/2026-04-18-sync-soak-unified-implementation-log.md`.
- Updated the unified todo with explicit reuse triage and kill criteria after
  user clarification.
- Updated `.codex/PLAN.md` to index the unified todo and implementation log.

Verification:

- Documentation-only change; no app tests run.
- Verified both new files exist and `.codex/PLAN.md` references them.

Open next:

- Start with S10 post-v61 signature drift proof and MDOT 1174R row-section
  key/state ownership.

## 2026-04-18 - Decomposition slice (plumbing, no device)

Controlling spec: `.codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`
Progress tracker: `.codex/checkpoints/2026-04-18-sync-soak-decomposition-progress.md`

What changed:

- **P0 device-lab split.** `tools/enterprise-sync-soak-lab.ps1` 2114 -> 144
  lines. Extracted:
  - `tools/sync-soak/ModuleLoader.ps1` (Flow.*.ps1 dot-source order +
    accepted flow catalog)
  - `tools/sync-soak/ResultIndex.ps1` (Write-SoakReadableResultIndex wrapper)
  - `tools/sync-soak/Environment.ps1` (Import-SoakEnvironmentSecrets)
  - `tools/sync-soak/DeviceLab.Arguments.ps1` (Test-SoakDeviceLabArguments)
  - `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1`
    (Invoke-SoakRefactoredFlow + ConvertTo-SoakActorSpecList)
  - `tools/sync-soak/DeviceLab.Legacy.ps1` (1794 lines, quarantined pre-
    refactor device-lab monolith; loud Write-Warning on entry)
- **FlowRuntime extraction.** Added `tools/sync-soak/FlowRuntime.ps1` (304
  lines) and converted SyncDashboard, Quantity, Photo, Contractors,
  DailyEntryActivity, Mdot0582B, Mdot1126Signature, Mdot1126Expanded, and
  Mdot1174R (summary only) to use shared preflight/final/summary helpers.
  Removed now-obsolete Complete-SoakMdot0582BSummary,
  Complete-SoakMdot1126SignatureSummary, Complete-SoakMdot1174RSummary.
  Net flow duplication reduction: -127 lines across 9 files.
- **Dart split.** `integration_test/sync/soak/soak_driver.dart` 1064 -> 46
  lines via `part`/`part of` into action mix, models, executors interface,
  runner, driver executor, backend/RLS executor, and personas.
- **Lock-in tooling.** Added `scripts/check_sync_soak_file_sizes.ps1` and
  `tools/sync-soak/size-budget-exceptions.json`. Advisory today, can gate
  CI with `-FailOnBlocked`.
- **Harness.** Updated `tools/test-sync-soak-harness.ps1` dot-source list
  and `$labSource` concatenation so existing flow-wiring greps still assert
  against the new decomposed module surface.

Why:

- Executes the P0 and lock-in slices of the sync-soak decomposition spec.
- Creates the foundation for the remaining extractions (MutationTargets,
  StorageProof, FormFlow) without touching accepted flows until the runtime
  seam is proven.

Exact gates run:

- `pwsh tools/test-sync-soak-harness.ps1` - PASSED (PS 7).
- `pwsh tools/enterprise-sync-soak-lab.ps1 -Flow sync-only
  -PrintS10RegressionRunGuide -Actors S10:4949:inspector:1` - printed 6
  ordered operator commands.
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` - exit 0
  (0 blocked without exception, 5 review-band entries).
- `dart analyze integration_test/sync/soak` - No issues found.
- `dart analyze integration_test test/harness` - No issues found.
- All 11 touched PowerShell files parse clean under PS 7 parser.

Known follow-ups (tracked in the decomposition spec):

- P0 item #4 (summary field structural test) still pending.
- P1 MutationTargets, ChangeLogAssertions, Cleanup split, StorageProof,
  FormFlow, ArtifactWriter split, and harness-self-test split are scheduled
  in `size-budget-exceptions.json` with expiresAfter 2026-06-30.
- Mdot1174R stays blocked for broad refactor until S21 acceptance is fixed.
- No S21/S10 live device run executed: this slice is plumbing-only.
  Per-flow acceptance semantics are preserved via opt-in switches
  (`-RequireActionCount`, `-RejectDirectSync`, `-Strict`) so the next
  accepted device run will still honour the same pass rules per flow.

Checklist items completed in this slice:

- Decomposition spec guardrails section.
- Endpoint definition bullets for module loading, argument normalization,
  environment/secret loading, actor conversion, flow runtime, artifact/
  evidence wrappers (preflight/final/summary), result-index export,
  legacy quarantine.
- Dart soak code split per target shape.
- Advisory line-count reporting + exception file.

Artifacts:

- None (no device run).
