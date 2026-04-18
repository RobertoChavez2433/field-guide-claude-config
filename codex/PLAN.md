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
  object-proof inputs. The S21 refactored `combined` gate is now green through
  daily-entry, quantity, and photo sequential mutate/sync/cleanup phases, S21
  `contractors-only` now proves the contractor/personnel/equipment graph, S10
  refactored regression is green through isolated daily-entry, quantity,
  photo, contractor, combined, and MDOT 1126 typed-signature flows, and S21
  `cleanup-only` live replay is green against accepted combined, contractor,
  and MDOT signature ledgers. The MDOT 1126 typed-signature and expanded
  fields/rows form-backed lanes are accepted on S21. The MDOT 0582B
  form-response mutation lane is also accepted on S21; export/storage proof for
  MDOT 0582B remains open. The MDOT 1174R lane is implemented/wired but not
  accepted; latest S21 diagnostics are blocked on compact workflow
  section/body proof while opening Quantities after QA edits, with cleanup and
  final queue drain proven.
  Remaining work starts with accepting MDOT 1174R, builtin form exports,
  saved-form/gallery lifecycles, S10 regression for newly accepted form lanes,
  role churn, broader storage/failure modes on S21/S10, staging proof, and
  backend actors running concurrently with device actors. Latest
  hardening: MDOT signature cleanup now fails closed on missing
  or mismatched storage `remotePath`, local database v61 makes
  `signature_files.local_path` nullable to match Supabase so cross-device
  signature metadata can pull, and S21 post-v61 signature backlog sync-only
  proof is green. MDOT 1126 expanded fields/rows are now S21-accepted through
  `20260418-s21-mdot1126-expanded-after-signature-ready-or-nav`, covering
  rainfall, SESC measures/status/corrective action, remarks, typed signature,
  storage proof, ledger cleanup, storage absence, and final empty queue.
- `2026-04-17-s21-soak-harness-audit-and-recovery-plan.md`:
  Focused pause-and-recover plan after repeated S21 all-modes failures. It
  audits the 2026-04-17 device-lab failure groups, records that the current
  monolithic soak script is too long and too generic for acceptance work, and
  defines the S21-first path: strict fail-loud harness gates, flow-level
  artifacts, mutation ledger/cleanup proof, single-flow S21 gates, then only
  later S10 and scale-up. The latest addendum audits the existing app-side HTTP
  driver server and host debug log server and records the no-third-server
  decision: the refactor should build thin client/orchestrator modules around
  the existing driver/debug surfaces, startup scripts, sync measurement script,
  and Dart soak/harness models. The scale-up model is S21 + S10 real-device
  proof, optional emulator if stable, headless app-sync actors for 10-20 app
  users, and backend/RLS virtual actors for remote pressure. Latest progress:
  the module split is live under `tools/sync-soak/`; the S21 `sync-only`,
  `daily-entry-only`, `quantity-only`, and `photo-only` state-machine paths are
  green as isolated single-flow gates; quantity and photo both use
  ledger-owned cleanup with UI-triggered cleanup sync; and photo now proves
  storage object download, delete, and absence against Supabase Storage.
  Cleanup hardening attempts ledger-owned restore/delete after post-mutation
  failures before recording a failed round, and the harness has reusable state
  sentinels for exact local/remote cleanup proof. Three-pass S21 confidence is
  now closed for `quantity-only` and `photo-only`; the refactored S21
  `combined` gate is green through the new module; S10 refactored regression is
  now green through the implemented flows; S21 cleanup-only replay is green
  against accepted ledgers; MDOT 1126 typed-signature form proof is green on
  S21, cleanup-only replay, and S10; and MDOT 1126 expanded fields/rows are
  green on S21. The MDOT 0582B mutation gate is now green on S21, with
  export/storage proof still open. The MDOT 1174R flow is wired and has live
  non-acceptance diagnostics. Current hardening moved the expanded-section
  sentinel onto the mounted body, made driver text entry visible/editable-only,
  removed the section-body `AnimatedSize`, kept repeated-row composer state
  alive while mounted, and added `Scrollable.ensureVisible` to the driver
  scroll route. That scroll-route patch is not accepted yet:
  `20260418-s21-mdot1174r-after-ensure-visible-scroll` failed loudly on a red
  screen during `mdot1174r-fields-and-rows` with duplicate GlobalKey/detached
  render-object runtime errors and local `form_responses` queue residue. The
  next mutation gate is recovering S21 through UI-triggered sync only, then
  fixing MDOT 1174R row-section key/state ownership before another S21
  acceptance attempt. After 1174R acceptance, continue to form exports and
  saved form/gallery lifecycles. The legacy all-modes runner is not a
  substitute.
- `2026-04-18-sync-soak-spec-audit-agent-task-list.md`:
  Current audit/task-list addendum mapping the remaining sync-soak and UI/RLS
  spec intent into parallel implementation-agent lanes. S10 regression, S21
  cleanup replay, and the first MDOT 1126 typed-signature form/signature lane
  are now artifact-backed; signature integrity-drift root cause is fixed in
  local schema v61 and S21 post-v61 backlog drain proof is artifact-backed,
  while S10 post-v61 cross-device proof remains open. MDOT 1126 expanded
  fields/rows and the MDOT 0582B mutation lane are accepted on S21; MDOT 1174R
  is implemented/wired but awaiting S21 acceptance after compact section/body
  and row-section state failures. Latest status: `visible-text-only` failed
  cleanly on Air/Slump scroll visibility and the follow-up
  `after-ensure-visible-scroll` failed loudly on duplicate GlobalKey/detached
  render-object runtime errors with queue residue. S21 was recovered afterward
  through the refactored Sync Dashboard `sync-only` flow and the live queue was
  empty. Current architectural guardrail work added custom lints for mounted
  form-section sentinels and for banning animated form body wrappers around
  keyed editable content. Next form-backed work is accepting MDOT 1174R,
  exports/gallery, role/account sweeps, storage/failure expansion, S10
  regression for newly accepted form lanes, and release/staging/scale gates.
- `reports/2026-04-18-enterprise-sync-soak-result-index.md` and
  `reports/2026-04-18-enterprise-sync-soak-result-index.json`:
  Compact human/machine audit of the 2026-04-18 enterprise sync-soak raw
  artifacts before cleanup. The index covers 55 runs, 15 passes, 40 failures,
  the MDOT 1174R red-screen/runtime failure, and the UI-only recovery run that
  drained the S21 queue.
- `reports/2026-04-18-all-test-results-result-index.md` and
  `reports/2026-04-18-all-test-results-result-index.json`:
  Full raw test-results audit before pruning. The index covers 165 runs, 76
  passes, 89 failures, and records every distinct failure class that must stay
  on the regression checklist. After this index was written, duplicate ignored
  raw `.claude/test-results/2026-04-18` output, local build caches, debug APKs,
  and exact generated S21 Download artifacts were cleaned. Tracked historical
  evidence remains; S10 app data/Downloads were not bulk-cleared.
- `2026-04-18-mdot-1126-typed-signature-sync-soak-plan.md`:
  Active implementation plan for the MDOT 1126 typed-signature sync-soak lane.
  It defines the isolated `mdot1126-signature-only` refactored flow, report
  attached form creation, local `change_log` proof for `form_responses`,
  `signature_files`, and `signature_audit_log`, signature storage download,
  ledger-owned cleanup, cleanup-only replay readiness, and the S21/S10
  acceptance sequence before role, RLS, failure-injection, staging, and scale
  expansion. Latest evidence: S21 isolated MDOT 1126, S21 cleanup-only replay
  of the accepted MDOT ledger, S10 isolated MDOT 1126, and S21 MDOT 1126
  expanded fields/rows and MDOT 0582B form-response mutation lanes are green.
  The next form-backed lane is accepting the already-wired MDOT 1174R flow,
  then builtin form exports and saved-form/gallery lifecycle sweeps.
- `2026-04-18-sync-engine-external-hardening-todo.md`:
  External sync-engine review addendum translating the PowerSync/Electric/
  WatermelonDB/RxDB/CouchDB/Syncable and local-first survey findings into a
  Field Guide hardening todo list. Current decision: do not replace the custom
  sync engine before the current release gates; run a bounded PowerSync spike
  later, with likely near-term adoption focused on checkpoints, scoped
  reconciliation, attachment queues, idempotent replay, and consistency
  contract documentation.

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
