# Plan Index

## Active Codex Plans In `.codex/plans/`

- `2026-04-08-lint-first-enforcement-plan.md`:
  Lint-first implementation queue for the current beta hardening wave,
  covering route-intent ownership, sync repair scaffolding, integrity
  diagnostics removal, bottom-sheet constraints, and the contract-test follow-up
  matrix.
- `2026-04-11-prerelease-central-tracker.md`:
  Canonical pre-release tracker replacing the old beta central tracker. This is
  now the primary source of truth for gate honesty, custom-lint enforcement,
  forms-first S21 validation, Office Technician / review-comment verification,
  pre-release blockers, CodeMunch structural debt, and final evidence gates.
- `2026-04-12-prerelease-final-canonical-tracker.md`:
  Concise current prerelease closeout tracker. Latest state: Google Cloud
  Vision OCR is live behind Supabase Edge Function/company opt-in, full OCR
  readiness passes, `codex-admin-sql` was deleted remotely, and the next active
  lane is PDF corpus hardening plus final tracker reconciliation.
- `2026-04-08-beta-research-inventory.md`:
  Durable Notion + CodeMunch audit artifact backing the central beta tracker,
  including current blocker reconciliation, routing audit results, and
  god-sized file inventory.
- `2026-04-08-codemunch-beta-audit-reference.md`:
  Standing CodeMunch-backed beta reference capturing the Notion export path,
  validated green slices, and the current god-sized decomposition queue.
- `2026-04-08-beta-testing-notes-spec.md`:
  Comprehensive implementation spec for the latest beta testing notes,
  including root-cause classification, contract-test backlog, lint-first
  candidates, and execution order across state ownership, forms, 0582B, trash,
  and resume/restoration issues.
- `2026-04-08-sync-status-merge-resolution-plan.md`:
  Product-direction and implementation plan for keeping `/sync/dashboard` as
  the single user-facing sync status surface while pushing raw diagnostics and
  merge tooling behind internal/debug seams.
- `2026-04-09-export-artifact-contract-plan.md`:
  Export-contract unification plan covering forms, daily entries, and pay
  applications without flattening their attachment and bundling differences.
- `2026-04-09-form-fidelity-standardization-spec.md`:
  Active spec for form export fidelity, shared section-based workflow shells,
  forms gallery restructuring, and the staged 1174R rollout.
- `2026-04-10-0582b-preview-sync-recovery-plan.md`:
  Active repair checklist for the reported 0582B preview/mapping gaps, shared
  PDF preview/navigation fixes, Samsung sync/background recovery proof, and the
  crash-safe resume checkpoint for removing runtime mock auth, re-verifying the
  Samsung device on a real-auth build, and tracking reopened live-device TODOs
  such as the inspector calendar create-project regression and pending
  project-backed 0582B validation.
- `2026-04-10-form-fidelity-device-validation-spec.md`:
  Controlling closure spec for the original-AcroForm fidelity lane, read-only
  preview separation, 0582B standards relocation/remapping, and the required
  two-pass real-auth Samsung verification across 0582B, 1174R, SESC 1126, and
  Daily Entries/IDR.
- `2026-04-10-form-workflow-regression-plan.md`:
  Active reopened regression tracker for the latest 0582B original/recheck
  numbering and double-text proof, SESC 1126 workflow/export/signature/discard
  issues, project-list local hydration, and 1174R performance/header/row-entry
  standardization work.
- `2026-04-11-pay-app-form-final-verification-plan.md`:
  Canonical implementation spec for the current pay-app/form-filler completion
  lane, including the G703-style running ledger workbook, compact pay-app
  dialog repair, form numeric keyboard progression, contractor comparison
  parity fixtures, final all-form fidelity verification, and the required
  self-review plus completeness-agent closeout gate.
- `2026-04-11-pay-app-form-contractor-review-final-verification-spec.md`:
  Current continuation spec for the pay-app e2e, contractor-comparison
  performance/order repair, all-cell AcroForm verification, and appended
  role/comment/photo/calculator TODOs.
- `2026-04-11-final-s21-verification-adaptive-idr-plan.md`:
  Current canonical final S21 completion plan for inspector contractor/equipment
  access, editable adaptive IDR direction, all-form all-cell verification,
  pay-app/contractor comparison closure, and final device evidence. Latest
  addendum: Daily Entry/IDR equipment-row proof requires at least five realistic
  equipment records per active Springfield contractor before acceptance.
- `2026-04-13-pay-app-export-tablet-analytics-spec.md`:
  Current working spec for the pay-app export UI, previous pay-app copy export,
  analytics pay-app/item drilldown, tablet daily-entry/quantities/projects
  layout repairs, quantity calculator styling, and S21 verification checklist.
- `2026-04-13-google-assisted-ocr-provider-plan.md`:
  Active research-backed plan for the Google Assisted OCR provider bakeoff,
  preserving two company-facing pipelines while comparing Vision image OCR,
  Vision raw-PDF OCR, Document AI Enterprise Document OCR, Form Parser, and
  Layout Parser against the prerelease/Springfield gates.
- `2026-04-13-google-assisted-ocr-fast-iteration-spec.md`:
  To-do style implementation spec for the Google Assisted OCR fast iteration
  loop, including the 8-pair Michigan corpus target, MDOT/AASHTOWare stress
  inputs, OCR-cache replay runner, cleanup policy, and final S10 verification
  gate.
- `2026-04-14-gocr-stage-trace-ground-truth-spec.md`:
  Controlling GOCR diagnostics and ground-truth discipline spec. Current
  direction: harden the baseline-plus-MDOT GOCR replay through exact
  comparison and single-endpoint traces. Latest focused MDOT state:
  `mdot_2026_04_03_estqua-pay-items` is at `675/677`; item-number pattern
  failures are resolved; the next implementation queue is the remaining
  `Traf Regulator Control` row collapse, the `Maintenance Gravel` row collapse,
  then a full original-baseline plus MDOT zero-regression replay.
- `2026-04-15-extraction-pipeline-decomposition-trace-spec.md`:
  Active verification gate before further MDOT heuristic iteration. Decompose
  the upstream PDF extraction pipeline in behavior-preserving slices while
  threading the existing `StageTrace`/debug system through every new substage
  with structured inputs, outputs, decisions, mutations, and provenance.
- `2026-04-15-pdf-extraction-heuristic-testing-standard.md`:
  Standing post-decomposition testing and iteration standard for PDF extraction
  heuristic changes, including the current original-four/full-corpus replay
  baselines, all manifest PDFs, canonical replay commands, artifact
  requirements, no-regression gates, and acceptance rules. Durable tracked copy
  lives at `docs/testing/pdf-extraction-heuristic-testing-standard.md`; the
  condensed agent rule lives at
  `.claude/rules/pdf/pdf-extraction-testing.md`.
- `2026-04-15-pdf-extraction-post-decomposition-todo.md`:
  Active to-do style tracker for the post-decomposition extraction iteration
  loop. Current evidence: fresh original-four replay reproduced the Berrien
  `16` mismatch baseline, fresh full-corpus replay reproduced `427` asserted
  mismatches plus `2` trace-contract failures, compact replay audit output now
  lands under `.claude/test-results/2026-04-15/`, and the most upstream
  confirmed first-bad stage is `text_recognition` via `ocr_source_error`.
  Priority 0 is now source/provider/rendering: prove a Vision table-region OCR
  route against the current full-page Vision cache before adding more
  downstream canonicalization. Existing notes show the previously tested
  Document AI processor underperformed Vision image OCR on Berrien/Huron/Grand
  Blanc, so Document AI is not the next retry unless a new processor/config
  hypothesis is defined.

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
