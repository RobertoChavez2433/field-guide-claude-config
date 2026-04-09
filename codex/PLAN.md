# Plan Index

## Active Codex Plans In `.codex/plans/`

- `2026-04-08-lint-first-enforcement-plan.md`:
  Lint-first implementation queue for the current beta hardening wave,
  covering route-intent ownership, sync repair scaffolding, integrity
  diagnostics removal, bottom-sheet constraints, and the contract-test follow-up
  matrix.
- `2026-04-08-beta-central-tracker.md`:
  Canonical append-only beta tracker. This is now the primary source of truth
  for phases, sprint slices, blocker status, verification status, and links to
  supporting beta artifacts. It also now carries the restart handoff for the
  Supabase/Docker environment state plus the next god-object decomposition
  slices.
- `2026-04-08-beta-research-inventory.md`:
  Durable Notion + CodeMunch audit artifact backing the central beta tracker,
  including current blocker reconciliation, routing audit results, and
  god-sized file inventory.
- `2026-04-08-codemunch-beta-audit-reference.md`:
  Standing CodeMunch-backed beta reference capturing the Notion export path,
  validated green slices, and the current god-sized decomposition queue.
- `2026-04-08-codemunch-beta-audit-reference.md`:
  Durable working reference for the current beta audit pass, including the
  Notion export path, the CodeMunch repo snapshot, and the live god-sized
  surface queue.
- `2026-04-08-beta-testing-notes-spec.md`:
  Comprehensive implementation spec for the latest beta testing notes,
  including root-cause classification, contract-test backlog, lint-first
  candidates, and execution order across state ownership, forms, 0582B, trash,
  and resume/restoration issues.

## Archived Codex Plans

Older Codex-authored plans and handoffs now live under
`.codex/plans/completed/` so the active folder stays focused on the live
tracker plus its supporting research artifact.

## Active Upstream Plans In `.claude/plans/`

- `2026-02-28-password-reset-token-hash-fix.md`:
  Current auth/password-recovery follow-up.
- `2026-02-22-testing-strategy-overhaul.md`:
  Open testing strategy blocker.
- `2026-02-22-project-based-architecture-plan.md`:
  Deployed architecture baseline and source of current multi-tenant rules.
- `2026-02-27-password-reset-deep-linking.md`:
  Prior password-reset implementation baseline.

## Codex Planning Policy

- Store new Codex-authored plans in `.codex/plans/`.
- Use `YYYY-MM-DD-<topic>-plan.md`.
- Reference existing `.claude/plans/` work from this index instead of
  duplicating it unless a Codex-specific addendum is needed.
- Keep `.claude/` as the deep reference library, not the default planning home
  for new Codex-authored plans.

## Historical Noise To Avoid

- `.claude/plans/completed/*`
- `.claude/backlogged-plans/*`

Load those only when a task depends on historical design rationale.
