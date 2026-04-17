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
- `2026-04-16-pdf-extraction-post-100-decomposition-trace-todo.md`:
  Active post-100% structural hardening tracker for the PDF extraction
  pipeline. It preserves the zero-mismatch/zero-trace-contract baseline while
  splitting new post-processing heuristics, row-data parsing, provenance, and
  test counterparts away from god-class/god-test shapes.
- `2026-04-16-external-pdf-heldout-validation.md`:
  Held-out first-try validation record for three PDFs outside the original
  four-plus-eight training corpus: Baraga municipal bid form, MDOT ESTQ&A
  schedule, and MDOT bid tab. Latest Windows Google capture and cache replay
  both ran `ocr_only` and passed count/item-number structural checks with zero
  expected failures, but native-text proxy evidence is explicitly not accepted
  as field-level truth. Current artifacts include rendered visual review pages,
  OCR candidate review ledgers, raw-to-final mutation CSVs, and S21
  `/sdcard/Download/FieldGuide_HeldOut_OCR_20260416/` device staging.
- `2026-04-16-heldout-ocr-generalization-hardening-spec.md`:
  To-do style follow-on spec for hardening OCR generalization after the first
  three held-out PDFs. It locks those three PDFs as baseline, expands the next
  iteration set to nine additional PDFs across the same three layout families,
  keeps exact no-normalization visual comparison as the acceptance rule, and
  tracks raw visual token preservation, confidence/auto-accept fidelity gaps,
  trace-token audits, app-level S21 verification, and the final baseline retry.
- `2026-04-16-android-codemagic-firebase-cicd-plan.md`:
  Active Android CI/CD setup plan for using GitHub release tags as the
  controlled beta switch, Codemagic as the single build/distribution system,
  Firebase App Distribution as the Android TestFlight equivalent, and
  `field-guide-beta-v<version>+<build>` as the shared iOS/Android beta label.
- `2026-04-16-manual-ui-rls-testing-checklist-plan.md`:
  Corrective checklist for the UI E2E feature-harness refactor, replacing
  route-only runner passes with manually driven S21/S10 bug-discovery sweeps,
  organized test-result artifacts, debug-log/sync review, and first-class
  RLS/role-boundary coverage.
- `2026-04-17-sync-system-hardening-implementation-checklist.md`:
  Codex working checklist for the seven-phase sync hardening and harness plan,
  deriving actionable gates from
  `.claude/plans/2026-04-16-sync-system-hardening-and-harness.md` and the
  controlling spec.
- `2026-04-17-sync-system-hardening-remaining-work.md`:
  Final handoff tracker for the sync hardening plan after implementation and
  commit split, covering the remaining Phase 7 staging, nightly-soak,
  auto-issue, observability, CI-history, and pre-alpha tag gates.
- `2026-04-17-sync-hardening-ui-rls-closeout-todo-spec.md`:
  Comprehensive to-do style closeout spec combining sync hardening remaining
  work with S21/S10 manual UI, role-boundary, RLS, sync-state, staging, and
  release-gate defects from the April 16-17 test artifacts.
- `2026-04-17-gocr-integration-branch-verification-remaining-work.md`:
  Branch-level verification closeout tracker for `gocr-integration`, capturing
  the hard blockers found after reviewing UI E2E, sync/auth hardening, Android
  Codemagic/Firebase, local Docker soak, staging soak, and GitHub CI evidence.
  Current state: workflow YAML parsing, Docker seed reset, staging harness
  password wiring, branch-tracked UI flow validators, local matrix, and local
  sync-engine performance are fixed/proven locally. Local Docker soak has been
  hardened and proven only as a concurrent backend/RLS stress test
  (`12368/12368` verified actions, 8 workers, 20 virtual users, 0 failures, 0
  RLS denials). It does not prove device sync because it bypasses local SQLite
  `change_log`, `SyncEngine`, storage bytes, app auth switching, and
  multi-device behavior. A host-side driver-app soak wrapper now exists for
  local SQLite/change-log evidence. Current S21/S10 one-device UI sync and the
  S21+S10 local device-lab wrapper passed on 2026-04-17 after fixing harness
  seed residue, fresh-backlog circuit breaker behavior, bounded full-sync push
  draining, and previous-user consent residue. Remaining work is GitHub run
  proof after push, staging soak/perf proof, expanded UI-driven device
  mutations, enterprise-scale actor/file/failure soak, and beta-tag
  distribution proof.
- `2026-04-17-enterprise-sync-soak-hardening-spec.md`:
  To-do style implementation spec for replacing generic soak confidence with a
  realistic multi-day sync testing system. It splits backend/RLS soak from
  device-sync soak, starts with the current one-device blocked queue failure,
  then builds toward S21/S10 multi-device actors, remote actors, real local
  `change_log` writes, file/storage bytes, role revocation, auth switching,
  realtime dirty scopes, failure injection, and complete triage artifacts.
- `2026-04-17-sync-soak-ui-rls-implementation-todo.md`:
  Live implementation checklist for the two April 17 sync specs. Current state:
  backend/RLS soak summaries and CI artifacts are explicitly labeled, the
  backend/RLS soak now uses the enterprise weighted action taxonomy with
  fixture version/hash, actor reports, and burst-window fields, the
  device-lab runner captures per-device UI-sync artifacts without
  `POST /driver/sync`, best-effort debug-log snippets and actor context
  snapshots are captured for local device-lab actors, driver change-log
  diagnostics now group blocked rows by table/operation/retry
  count/project/error, and the lab runner has optional true UI daily-entry
  activity mutation, host-side failure-injection, and Supabase Storage
  object-proof inputs. Remaining work starts with UI-driven quantities/photos/
  forms/signatures/personnel mutations, role churn, actually running the
  storage/failure modes on S21/S10, staging proof, and backend actors running
  concurrently with device actors.

## Active Codex Research In `.codex/research/`

- `2026-04-17-sync-soak-gap-research.md`:
  Research and code-audit memo explaining why the clean 12,368-action
  backend/RLS soak does not prove device sync. It records external references
  from Microsoft load-testing docs, Android testing strategy, SQLite WAL,
  Supabase RLS, Supabase Storage RLS, and Supabase Realtime limits, then maps
  those expectations to the current app sync gaps.

## Active Codex Checkpoints In `.codex/checkpoints/`

- `2026-04-17-sync-soak-implementation-checkpoints.md`:
  Append-only checkpoint log for the enterprise sync soak and UI/RLS closeout
  implementation. Use this for slice-by-slice notes about what was found, what
  changed, what was verified, and what must stay open while the specs remain
  the actual verification gates.

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
