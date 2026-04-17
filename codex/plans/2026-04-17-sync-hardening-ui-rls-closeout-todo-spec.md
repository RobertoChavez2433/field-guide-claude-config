# Sync Hardening Closeout + UI/RLS Defect Repair Spec

## Summary

Use `.codex/plans/2026-04-17-sync-system-hardening-remaining-work.md` as the
controlling remaining-work tracker. Phases 1-6 and most Phase 7 repo scaffolding
are already implemented; do not rebuild them. The remaining closeout is:
product-intent fixes, realistic fixture expansion, role-boundary/UI defects from
the S21/S10 sweeps, staging/observability proof, CI history, and final ship-bar
evidence.

Trusted evidence:

- Plan trackers:
  `.codex/plans/2026-04-17-sync-system-hardening-implementation-checklist.md`,
  `.codex/plans/2026-04-17-sync-system-hardening-remaining-work.md`
- Manual sweep:
  `.claude/test-results/2026-04-16_2058-manual-ui-rls-sweep-s21/findings.md`
- Role rerun:
  `.claude/test-results/2026-04-17_0225-role-boundary-rerun-s21-s10/findings-clean.jsonl`
- Treat the role rerun as authoritative for role-boundary retest status. The
  S10/S21 toolbox/gallery/calculator crash is fixed and should not be reopened
  unless it reproduces again.

## 2026-04-17 Repo-Side Implementation Pass Status

Completed in this pass:

- [x] Daily Entry activities are owned by the Activities tab, render as
  location-grouped text, preserve legacy plain text, export grouped location
  headings to PDF data, and use more tablet left-pane width.
- [x] Weather auto-fetch is limited to newly created entries and no longer runs
  merely because an existing entry loads with missing weather.
- [x] PDF import preview/confidence screen now has regression coverage proving
  `Import` calls the real `BidItemProvider.importBatch` apply path, enters a
  loading state, reports retry-visible errors, and reloads callers only after a
  successful preview import result.
- [x] Local harness fixture SQL now seeds the larger graph shape for p001-p003:
  4 contractors/project, 5 equipment/contractor, 50 bid items/project,
  4 personnel types/project, 20 entries/project, one photo/entry,
  location-grouped activities JSON, and entry-linked `form_responses` for
  0582B, 1174R, 1126, and IDR.
- [x] Fixture parity validator and script tests enforce the expanded fixture
  shape and entry-linked form coverage.
- [x] Inspector/admin route and UI boundaries were tightened for project
  create/remove/archive/delete controls, import preview routes, pay-app detail
  and compare routes, trash visibility, `/settings/trash`, `/admin-dashboard`,
  and `/project/new`.
- [x] Review-summary deep link renders its screen instead of redirecting to the
  dashboard, with overflow-safe empty-state layout.
- [x] Driver-visible sentinels were added for edit profile, admin dashboard,
  and form PDF preview.
- [x] Quantities no-project state disables export/import actions instead of
  leaving misleading actions enabled.
- [x] Gallery thumbnails now show an explicit missing-image state when seeded
  files are unavailable.
- [x] To-Do add/edit dialog content and footer controls are constrained/wrapped
  to reduce S21 clipping.
- [x] Realtime sync hint registration prunes stale and excess active
  subscriptions before enforcing the max-active cap.
- [x] Nightly soak workflow is retargeted to staging credentials and no longer
  performs a local Supabase reset.
- [x] Harness auth accepts `HARNESS_SUPABASE_PASSWORD`, defaults only for local
  Docker, and rejects staging use of the local-only password.
- [x] GitHub auto-issue policy suppresses new issues for fingerprints closed in
  the last 24 hours while preserving open-issue updates.
- [x] Quantities app-bar PDF import and pay-app export controls now require
  project-management permission instead of broad field-edit permission, so
  inspector-level access cannot start those management flows from the
  Quantities screen.

Still open after this repo-side pass:

- [ ] Full staging fixture provisioning path with staging-only harness password
  and staging sign-in proof.
- [ ] Local reset, sync matrix, soak, and performance proof rerun against the
  expanded fixture; update `scripts/perf_baseline.json` only after acceptance.
- [ ] Real S21/S10 reruns for admin, inspector, engineer, and office technician
  sessions with no `MOCK_AUTH`.
- [ ] Trash cross-role record isolation proof with seeded cross-role trash
  records and real sessions.
- [x] Stale S21/S10 sync state, fresh-backlog circuit-breaker behavior, and
  harness-company mismatch were investigated and fixed for the captured device
  failures.
- [ ] Sync Dashboard `/sync/status` reconciliation and remaining runtime
  sync-noise triage.
- [ ] Broader stranded-route/back-shell sweep beyond the review/draft routes
  touched in this pass.
- [ ] Full project download/import graph assertion after sync, not just import
  runner or PDF bid-item apply behavior.
- [ ] Remaining feature bugs not addressed here: Entry PDF export failure,
  Pay App comparison XLSX path, form viewer compact labels, dashboard seeded
  project state, Projects -> Dashboard bottom-nav switch, and any still-reproing
  S21 overflow.
- [ ] External Phase 7 gates: staging schema hash parity, Supabase Log Drains to
  Sentry, Sentry repository dispatch proof, staging performance proof, three
  green 10-minute staging soaks, three green 15-minute nightly soaks, full test
  PR gate, five ship-bar confirmation, and pre-alpha tag.

## Implementation TODOs

### 1. Product-Intent Blockers

- [x] Rework Daily Entry activities so locations are owned by the Activities
  tab, not the Header card.
- [x] Render and export activities grouped under location headings across
  editor, preview, review/list cards, and PDFs.
- [x] Preserve safe rendering for legacy plain-text `daily_entries.activities`.
- [x] Update tablet layout so Activities uses the available left-side width
  instead of leaving dead horizontal space.
- [x] Change weather auto-fetch so it runs only once for newly created entries;
  editing/viewing existing entries with missing weather must not fetch or append.
- [x] Fix project import confidence-screen `Import` so it calls the real apply
  path, exposes loading/error/disabled states, and leaves observable imported
  project graph data after success.

### 2. Fixture + Harness Corrections

- [x] Scale local Docker and staging fixture data to realistic graph size:
  4 contractors/project, 5 equipment/contractor, 50 bid items/project,
  4-5 personnel types/project, 20 daily entries/project, and at least 1 photo
  per daily entry.
- [x] Seed activities as location-grouped JSON, not flat activity strings.
- [x] Add entry-linked `form_responses` for 0582B, 1174R, 1126, and IDR using
  `entry_id` plus `project_id`.
- [x] Update `scripts/validate_harness_fixture_parity.py` and SQL probes to
  enforce the expanded fixture counts and entry-linked form coverage.
- [ ] Re-run local reset, matrix, soak, and performance proof after fixture
  expansion; update `scripts/perf_baseline.json` only after the larger fixture
  is accepted.
- [x] Add `HARNESS_SUPABASE_PASSWORD` support to harness auth config: default to
  `HarnessPass!1` only for local Docker, require staging secret override for
  staging.
- [ ] Add a guarded staging fixture provisioning path that reuses deterministic
  IDs but never uses the local-only password on staging.

### 3. Permission Boundary Repairs

- [ ] Hide and block inspector project create/delete/remove/archive controls on
  S21 and S10 while preserving inspector visibility and edit access for assigned
  projects.
- [ ] Hide and block inspector PDF import controls on S21 and S10.
- [ ] Hide and block inspector pay-application management/detail/delete/compare
  access on S10 and S21 unless a later product rule explicitly allows read-only
  detail.
- [ ] Hide and block Trash tile and `/settings/trash` route for inspector,
  engineer, and office technician; only admin may access account-wide trash
  unless product policy changes.
- [x] Add route-level guards, not just widget hiding, for all denied surfaces.
- [ ] Prove trash cross-role record isolation with real sessions and seeded
  cross-role trash records; current runs only proved tile/route visibility and
  left record isolation blocked.
- [ ] Add real engineer and office technician credentials or staging harness
  personas so both roles are tested on S21 and S10 without `MOCK_AUTH`.

### 4. Sync State + Observability Repairs

- [x] Investigate and fix stale sync state from both runs: S10
  `pending/unprocessed ~1680`, S21 role rerun `pending/unprocessed` counts with
  blocked rows, and `change_log exceeds 1000` circuit breaker.
- [x] Fix harness/company mismatch where seeded `harness-company-001` rows push
  under a real user company and poison sync.
- [x] Fix realtime hint subscription leak:
  `register_sync_hint_channel: too many active subscriptions (max 10)`.
- [ ] Reconcile Sync Dashboard UI with `/sync/status`; UI must not show
  repair/blocked items when debug status reports clean, or debug status must
  expose the same blocked state.
- [ ] Investigate extra runtime sync noise:
  `setState() or markNeedsBuild() called when widget tree was locked`,
  signature integrity-drift counts, and BaseListProvider daily-entry update
  failures.
- [ ] Keep `SyncCoordinator` as the sync entrypoint, preserve `SyncRegistry`
  order, keep `change_log` trigger-owned, restore `sync_control.pulling` in
  `finally`, and preserve `42501` as non-retryable.

### 5. Navigation, Route, and Sentinel Repairs

- [ ] Fix root/deep-link back behavior or shell wrapping for stranded routes:
  `/entries`, `/forms`, `/form/:id`, `/pay-app/:id`, `/quantities`,
  `/quantity-calculator/:entryId`, `/analytics/:projectId`, `/gallery`,
  `/toolbox`, `/calculator`, `/todos`, `/sync/conflicts`, and project setup
  Contractors.
- [ ] Fix Projects -> Dashboard bottom-nav switch from `/projects`.
- [ ] Fix dashboard seeded-project state so feature cards render without
  requiring manual project recovery.
- [x] Fix `/review-summary` so it renders the review summary instead of
  redirecting to dashboard.
- [ ] Decide and encode the correct form deep-link target: if
  `/form/:responseId` should open `form_viewer_screen`, update flows; if it
  should open `mdot_hub_screen`, fix routing.
- [x] Add or correct driver-visible sentinels for real visible screens/dialogs:
  `entry_editor_screen`, `form_pdf_preview_screen`, `form_export_dialog` and
  actions, `edit_profile_screen`, `admin_dashboard_screen`.
- [ ] Fix Saved Exports tile/deep link so it opens `/settings/saved-exports`,
  not `/projects`.
- [ ] Fix Settings Trash tile for admin so it opens `trash_screen` while
  remaining denied to non-admin roles.
- [ ] Fix PDF import preview route/sentinel confusion after successful
  extraction; `pdf_preview_screen`, select-all, and import controls must become
  driver-visible.

### 6. Feature-Specific UI/Runtime Bugs

- [ ] Fix Entry PDF export `PDF generation failed`.
- [ ] Fix Pay App comparison missing XLSX path; harness pay-app data must use a
  real existing export artifact or gracefully generate/load one.
- [ ] Fix Quantities `No Project Selected` state when seeded/selected project
  context is expected.
- [ ] Fix Quantities export action from no-project state: either disable with
  clear explanation or open the intended export hub when context exists.
- [x] Fix Gallery thumbnails so seeded photos render real previews or an
  explicit missing-image state, not generic placeholders for all items.
- [x] Fix To-Do add/edit dialog clipping on S21.
- [ ] Fix S21 role-boundary overflow:
  `RenderFlex overflowed by 139 pixels on the right`.
- [ ] Clean form viewer action labels so plus/copy is not duplicated and labels
  remain compact on S21.

### 7. Phase 7 CI, Staging, and Release Gates

- [x] Retarget `.github/workflows/nightly-soak.yml` fully to staging: no local
  reset, staging URL/anon key only for Flutter steps, no service-role key
  exposure.
- [x] Extend `scripts/github_auto_issue_policy.py` to enforce
  1 issue/fingerprint/24h across recently closed issues.
- [ ] Provision dedicated staging Supabase, apply migrations, seed corrected
  fixture with staging-only password, and verify admin + inspector sign-in.
- [ ] Verify local/staging schema hash parity with `scripts/hash_schema.py`.
- [ ] Prove Supabase Log Drains into Sentry for `postgres_logs`, `auth_logs`,
  and `edge_logs`; run
  `deno test supabase/functions/_shared/log_drain_sink.test.ts`.
- [ ] Configure Sentry `repository_dispatch` to
  `.github/workflows/sentry-auto-issue.yml`; prove fatal creates/updates an
  issue and warning remains digest-only with hashed identifiers only.
- [ ] Run staging performance proof: cold full sync <= 2000ms, warm foreground
  <= 500ms, perf regression script passes against baseline.
- [ ] Collect three consecutive green 10-minute staging CI soaks and three
  consecutive green 15-minute staging nightly soaks.
- [ ] Run one full test PR through staging schema, soak, perf, service-role
  preflight, and auto-issue policy gates.
- [ ] Confirm all five ship bars at the same commit, then cut the
  pre-alpha-eligible tag.

## Test Plan

- Unit/model: grouped activity serialization, weather fetch-on-create-only,
  import apply controller, harness password override, auto-issue
  closed-fingerprint suppression.
- Widget/UI: per-location activity editors, tablet Activities layout, no
  header-owned location selector, admin/non-admin permission control visibility,
  S21 To-Do dialog fit, form/export/screen sentinels.
- Route/driver: all stranded routes have a working back path or shell nav;
  denied role routes are blocked; PDF import preview, Saved Exports, Trash,
  Review Summary, form response, and project import flows expose correct
  sentinels.
- Sync/harness: fixture parity, expanded SQL probes, matrix RLS visibility,
  entry-linked form response visibility, stale sync/circuit-breaker regression,
  realtime subscription leak regression.
- Device/manual: rerun S21 + S10 role-boundary matrix with admin, inspector,
  engineer, and office technician real sessions; rerun manual UI sweep for
  previously failed features; screenshots/logs/sync status must be clean.
- CI/staging: `flutter analyze`, `dart run custom_lint`, sync validators,
  fixture validator, script unit tests, local reset, local/staging performance
  proof, 10-minute staging soak, 15-minute nightly staging soak, Sentry/Log
  Drain proof.

## Assumptions

- No `MOCK_AUTH`; all auth, RLS, sync, and role checks use real sessions and
  backend state.
- The role-policy corrections from the rerun stand: inspectors may view
  analytics and edit assigned projects, but may not create/delete/archive/remove
  projects or access PDF import/pay-app management/trash.
- The role-boundary rerun supersedes earlier noisy/invalid attempts for role
  status; the broader manual sweep remains valid for feature/UI failures not
  retested.
- The existing Phase 1-6 implementation is preserved unless a failing
  acceptance gate proves a targeted regression fix is needed.
- If a test is hard to write honestly, extract a real production seam; do not
  add test-only production hooks.
