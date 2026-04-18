# Sync System Hardening Implementation Checklist

Source plan: `.claude/plans/2026-04-16-sync-system-hardening-and-harness.md`
Controlling spec: `.claude/specs/2026-04-16-sync-system-hardening-and-harness-spec.md`

## Operating Gates

- [ ] Work one phase at a time, in order.
- [ ] Before advancing phases, reread the plan/spec section for the completed phase and confirm intent coverage.
- [ ] Keep `SyncCoordinator` as the only sync entrypoint.
- [ ] Preserve `SyncRegistry` adapter order and keep `scripts/validate_sync_adapter_registry.py` green.
- [ ] Preserve `SyncErrorClassifier` as sync error classification owner.
- [ ] Preserve `SyncStatus` as transport state authority.
- [ ] Preserve trigger-owned `change_log`; never insert directly.
- [ ] Preserve `sync_control.pulling` suppression brackets with `finally` restoration.
- [ ] Preserve RLS company scope through `get_my_company_id()`.
- [ ] Preserve SQLSTATE `42501` as non-retryable security-boundary failure.
- [ ] Preserve `is_builtin = 1` server-seeded skips.
- [ ] Do not use `MOCK_AUTH`.
- [ ] Do not add test-only production hooks, methods, or lifecycle APIs.
- [ ] Keep `flutter analyze`, `dart run custom_lint`, and existing validators green.

## Phase 1: Local Docker Supabase + Seeded Fixture

- [x] Create `tools/supabase_local_start.ps1`.
- [x] Create `tools/supabase_local_reset.ps1` with local-host guard for `SUPABASE_DATABASE_URL`.
- [x] Replace `supabase/seed.sql` with deterministic local-only harness fixture.
- [x] Seed exactly one harness company.
- [x] Seed 12 paired `auth.users` and `auth.identities` rows with password `HarnessPass!1`.
- [x] Seed role distribution: admin=1, engineer=2, office_technician=1, inspector=8.
- [x] Seed matching approved `user_profiles` rows using actual post-migration columns only.
- [x] Document deprecated `viewer` fallback as unreachable in seed and covered later by auth matrix.
- [x] Seed 15 projects `p001` through `p015`.
- [x] Seed project assignment matrix:
  - [x] i001/i002 -> p001,p002,p003.
  - [x] i003/i004 -> p004,p005,p006.
  - [x] i005/i006 -> p007,p008,p009.
  - [x] i007 -> p010,p011.
  - [x] i008 -> p012,p013.
  - [x] Engineers -> p001 through p013.
  - [x] Office technician -> p014,p015.
  - [x] Admin has no explicit assignment.
  - [x] p014,p015 unassigned to inspectors.
  - [x] i008 created after p001 and not seed-assigned to p001.
- [x] Seed FK graph under p001,p002,p003:
  - [x] At least 2 locations per project.
  - [x] At least 2 contractors per project.
  - [x] At least 2 equipment rows per project through contractors.
  - [x] At least 2 bid items per project.
  - [x] At least 2 personnel types per project.
  - [x] At least 1 daily entry per project referencing a same-project location.
  - [x] At least 1 photo per daily entry with deterministic storage paths.
- [x] Do not seed change_log, sync_control, builtin inspector forms, or Phase 3 on-demand feature tables.
- [x] Wrap seed in `BEGIN`/`COMMIT` and use idempotent inserts.
- [x] Create `scripts/validate_harness_fixture_parity.py`.
- [x] Add unit tests for the fixture parity parser/validator.
- [x] Verify `pwsh -File tools/supabase_local_reset.ps1`.
- [x] Verify local sign-in smoke for admin and inspector1.
- [x] Verify fixture SQL probes from the plan.
- [x] Verify reset wrapper refuses non-local `SUPABASE_DATABASE_URL`.
- [x] Verify `python scripts/validate_sync_adapter_registry.py`.
- [x] Verify live schema contract against local Docker when local DB is available.
- [x] Verify `flutter analyze`.
- [x] Verify `dart run custom_lint`.

Phase 1 evidence note: local Supabase CLI v2.84.2 consistently returns a
post-seed storage health-check 502 after `Seeding data from supabase/seed.sql...`.
`tools/supabase_local_reset.ps1` treats only that exact post-seed race as
recoverable after `supabase status` succeeds. Migration/seed failures still exit
non-zero.

## Phase 2: Harness Driver Skeleton

- [x] Create harness fixture cursor constants matching the seed.
- [x] Create harness auth config that refuses service-role keys in Flutter runtime.
- [x] Create local/staging harness environment loader.
- [x] Create role persona login helpers for admin, engineers, office technician, and inspectors.
- [x] Create driver harness entrypoints under `integration_test/sync/harness/`.
- [x] Drive the real Flutter client against local Supabase.
- [x] Assert real RLS responses without mock auth.
- [x] Add skeleton tests for login, profile load, assigned project visibility, and service-role exclusion.
- [x] Make `scripts/validate_harness_fixture_parity.py` enforcing against cursor constants.
- [x] Run Phase 2 harness tests as hard gate.

Phase 2 evidence note: `flutter test test/harness` passes the unit-speed
helper suite, and
`flutter test test/harness/harness_live_supabase_test.dart --dart-define=RUN_LOCAL_HARNESS=true`
passes against local Docker Supabase. The live smoke signs in with seeded
credentials and verifies admin profile load plus inspector1 RLS project
visibility. Static guards for hardcoded `Key('...')`, direct `SyncEngine.`,
`supabase.co`, and direct `emit_sync_hint` references return zero matches.

## Phase 3: Full-Surface Correctness Matrix

- [x] Add matrix coverage for auth, projects, assignments, entries, photos, signatures, 0582B, 1174R, 1126, IDR, pay apps, quantities, equipment, contractors, personnel, locations, todos, consent, support, documents, and exports.
- [x] Cover admin, engineer, office_technician, inspector, and deprecated viewer fallback behavior.
- [x] Assert no cross-role visibility violations on any frame.
- [x] Add deterministic failing repro for inspector unassigned-project refresh leakage.
- [x] Add deterministic failing repro for flashing metadata on new project creation.
- [x] Add deterministic failing repro for new-user-to-old-project assignment failure.
- [x] Add deterministic failing repro for download-on-click failure.
- [x] Add deterministic failing repro for single-account refresh bleed.
- [x] Add on-demand sync test data helpers only through production-shaped fixture seams.
- [x] Keep driver registry, contract registry, and flows in sync for any changed screen contracts.
- [x] Run the full Phase 3 correctness matrix as hard gate.

Phase 3 evidence note: every required `integration_test/sync/matrix/*_test.dart`
file exists, and defect repros are tagged `defect-a` through `defect-e`.
The Windows `integration_test` device runner is blocked before test code by the
existing desktop CMake/JNI setup, so the hard local gate is
`test/harness/harness_sync_matrix_local_test.dart`, which imports the same
matrix bootstrap and passed against local Docker Supabase with
`--dart-define=RUN_LOCAL_HARNESS=true`. Existing sync characterization tests
passed unchanged. Analyzer, custom_lint, adapter registry validation, and
static guards for hardcoded `Key('...')`, direct `SyncEngine.`, and direct
`emit_sync_hint` references are clean.

## Phase 4: Logging Event-Class Audit + Sentry Dual-Feed

- [x] Produce logging event-class audit report against the spec’s locked event list.
- [x] Create `scripts/audit_logging_coverage.ps1`.
- [x] Add log seams for all must-log sync/auth/project-selection methods.
- [x] Wire client-side Sentry forwarding for warning/error/fatal classes only.
- [x] Add event sampling for high-volume non-error classes.
- [x] Add 60-second pre-Sentry fingerprint dedup buffer.
- [x] Add 50 events/user/day rate limit.
- [x] Enforce breadcrumb budget of 30 per event.
- [x] Wire in-app problem reporting to Sentry with recent logs, user id, project id, and device info after PII filtering.
- [x] Define and document Supabase Log Drain sink decision for staging.
- [x] Add unit tests for filter, dedup, rate-limit, and breadcrumb trimming.
- [x] Run audit script, Sentry filter tests, lint, and sync validators as hard gate.

Phase 4 evidence note: added `LogEventClasses`, sampling filter, dedup/rate
middleware, Sentry runtime flags, transport middleware wiring, core
`authStateTransition` and `rlsDenial` seams, and CI architecture steps for
logging audit plus harness fixture parity. Added custom HTTP Supabase Log Drain
shared sink with fixture scrub tests under `supabase/functions/_shared/`, and
extended `SentryFeedbackLauncher.captureProblemReport` to attach scrubbed recent
logs, user id, project id, and device info. `flutter test
test/core/logging/logger_sentry_filters_test.dart`, `pwsh -File
scripts/audit_logging_coverage.ps1`, `python scripts/validate_harness_fixture_parity.py`,
`python scripts/validate_sync_adapter_registry.py`, targeted analyzer, and
custom_lint pass. `deno test supabase/functions/_shared/log_drain_sink.test.ts`
could not run locally because `deno` is not installed in this workspace; the test
file is committed for the Supabase/Deno runtime gate.

## Phase 5: Property-Based Concurrency + Soak

- [x] Add `glados` dependency or documented table-driven fallback where needed.
- [x] Add properties for LWW conflict winners and clock-skew fallback.
- [x] Add properties for cursor monotonicity.
- [x] Add properties for pull-scope enrollment and teardown.
- [x] Add properties for tombstone propagation.
- [x] Create local soak action driver with configurable 5/10/15 minute duration.
- [x] Implement weighted action mix: 30% reads, 30% entry mutations, 15% photo uploads, 20% deletes/restores, 5% role/assignment changes.
- [x] Create `scripts/soak_local.ps1`.
- [x] Add CI 10-minute soak initially stabilized per plan.
- [x] Add nightly 15-minute soak workflow.
- [x] Run local PBT suite and 10-minute soak as hard gate.

Phase 5 evidence note: added `glados` plus shared invariant registration for
unit-speed and integration/device contexts, table-driven fallback coverage, and
headless local harness mirrors for CI-safe execution. Added `SoakDriver`,
metrics parsing, local/driver executors, `scripts/soak_local.ps1`, a
sync-touching 10-minute quality-gate step, and nightly 15-minute soak workflow.
The role-assignment soak action uses the production
`admin_upsert_project_assignment` / `admin_soft_delete_project_assignment` RPC
boundary, then refreshes the assignment row. A fresh-migration defect where the
final RPC definition lost its restore flag was fixed in
`20260417010000_fix_project_assignment_upsert_restore.sql` and covered by
`test/scripts/project_assignment_rpc_migration_test.py`. Final local gates:
`flutter test test/harness`, sync property tests, sync characterization tests,
fixture parity, adapter registry validation, analyzer, custom_lint, and Python
script tests all passed. Final local soak after the RPC-refresh fix:
`pwsh -File scripts/soak_local.ps1 -DurationMinutes 10 -UserCount 20` passed
with 16,766 actions, 832 role-assignment mutations, 0 errors, and 0 RLS denials.

## Phase 6: Sync Engine Rewrite

- [x] Profile cold-start full sync, warm foreground unblock, and cold empty-state placeholder/fill against Phase 1 fixture.
- [x] Preserve public contracts unless profiling evidence triggers the escape clause.
- [x] Rewrite targeted hotspots for parallel table pulls where dependency-safe.
- [x] Rewrite change-log cursor advancement hotspots.
- [x] Rewrite pull-scope enrollment hotspots.
- [x] Rewrite realtime-hint fan-out hotspots.
- [x] Fix assignment filter ordering before first project-list render.
- [x] Fix all five committed defect repros.
- [x] Keep all characterization tests green or replace them with more honest harness coverage in documented commits.
- [x] Re-profile and prove cold-start full sync <= 2 seconds locally.
- [x] Prove warm foreground unblock <= 500ms.
- [x] Prove cold empty-state <= 500ms and fill <= 2 seconds.
- [x] Run Phase 3 matrix, Phase 5 PBT/soak, lint, and validators as hard gate.

Phase 6 evidence note: added `docs/sync-phase6-profiling.md` and
`test/harness/sync_performance_local_test.dart`. The local seeded fixture
measured 471ms median cold full sync and 138ms median warm quick sync after the
Phase 6 hardening, both below the spec ceilings. No public sync entrypoint or
registry-order escape clause was used; existing targeted protections remain:
one cursor write per table, hoisted local-column reads, materialized pull scope,
same-cycle assignment enrollment, and FK rescue under trigger suppression. Added
structured `sync.fk_rescue` logs to rescue paths. Project list auth/refresh now
loads assignments and projects behind a silent barrier before post-load notify,
with inspector lists and selection fail-closed while assignments are absent.
Download confirmation now awaits the production sync result and keeps failed
imports failed when sync returns errors. Gates passed: clean local reset,
`test/harness/harness_sync_matrix_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true`,
project provider tests, full project list screen tests, sync FK/pull tests,
sync property + glados tests, sync characterization tests, performance harness,
adapter registry validation, schema parity, logging audit, analyzer,
custom_lint, harness fixture parity, Python script tests, and
`pwsh -File scripts/soak_local.ps1 -DurationMinutes 10 -UserCount 20` with
16,700 actions, 0 errors, and 0 RLS denials.

## Phase 7: Staging Supabase + CI Gate + GitHub Auto-Issue Policy

- [x] Record external staging provisioning requirements in the PR/implementation notes.
- [x] Create `scripts/hash_schema.py`.
- [x] Create `.github/workflows/staging-schema-gate.yml`.
- [x] Create `scripts/github_auto_issue_policy.py`.
- [x] Create `scripts/check_perf_regression.py`.
- [x] Create `scripts/perf_baseline.json`.
- [x] Retarget canonical 10-minute CI soak to staging.
- [x] Ensure service-role key is never exposed to Flutter workflow steps.
- [x] Add preflight guard for service-role exclusion.
- [x] Add staging schema hash gate to quality workflow.
- [x] Add +10% / 2000ms performance regression gate.
- [x] Wire nightly soak output into the shared auto-issue policy.
- [x] Wire Sentry webhook events into the shared auto-issue policy.
- [x] Verify issue policy dedup, thresholds, severity routing, rate limit, auto-close, and hashed identifiers.
- [ ] Re-run 2-second profiling against staging.
- [ ] Confirm all five ship-bar conditions hold simultaneously.
- [ ] Cut the pre-alpha-eligible tag only after all ship bars are true.

Phase 7 evidence note: repo-side implementation is complete. Added
`docs/sync-phase7-staging-ops.md` for external provisioning and ship-bar ops,
`scripts/hash_schema.py`, `scripts/github_auto_issue_policy.py`,
`scripts/check_perf_regression.py`, `scripts/perf_baseline.json`,
`.github/workflows/staging-schema-gate.yml`, and
`.github/workflows/sentry-auto-issue.yml`. The quality gate now calls the
staging schema reusable workflow, routes lint findings through the shared
auto-issue policy, retargets the canonical 10-minute soak to staging using only
staging URL/anon credentials, adds a service-role preflight, records soak/perf
artifacts, and enforces the +10%/2000ms perf gate. Nightly soak now updates the
three-green-night repository variables and sends failures through the shared
policy. Added script unit tests for schema hashing, perf regression, and
auto-issue policy behavior, plus a JSONL sample fixture. Local gates passed:
`python -m unittest discover -s test/scripts -p "*_test.py"`, direct
`github_auto_issue_policy.py` sample run, `check_perf_regression.py` baseline
self-check, local `hash_schema.py` against Docker Supabase, targeted analyzer,
Python compile, `git diff --check`, and a 1-minute soak smoke that wrote the CI
metrics artifact. The remaining three Phase 7 items are intentionally external:
they require provisioned staging secrets/resources and three stable CI/nightly
runs before the staging 2-second measurement, ship-bar confirmation, and
pre-alpha tag can be completed.
