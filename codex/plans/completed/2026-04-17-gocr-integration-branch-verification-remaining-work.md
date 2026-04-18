# GOCR Integration Branch Verification Remaining Work

Branch reviewed: `gocr-integration`
Clean branch HEAD reviewed: `cffadc9eaca0ecfce2c63d9524e0c8b1cbff76be`
Implementation pass HEAD: `3f2cd2b830a3877e85a74415bdbf47e8bcd1ba71`
Merge base with `origin/main`: `29c6ea68aec99c4008537b581889a11eff6739d4`
Review date: 2026-04-17

## Summary

The branch is not at "only dual-device runs left." The three reviewed lanes are
all partially implemented, but hard repo/CI/harness blockers remain before final
S21/S10 real-session sweeps are meaningful.

Verdicts:

- UI E2E feature harness: partial.
- Sync/auth/role hardening: partial.
- Android Codemagic/Firebase CI/CD: partial.

Primary blockers:

- GitHub Actions workflow parsing, the local Docker seed reset, and
  quality-gate staging password wiring are fixed locally and need the next
  pushed GitHub run to confirm CI job startup.
- Local Docker matrix and local sync-engine performance gates pass on the
  expanded fixture, but local timings are not device/staging proof.
- Android Codemagic/Firebase wiring exists, but no real beta-tag distribution
  run has been proven.
- Real S21/S10 sync timing must be captured through the UI with
  `tools/measure-device-sync.ps1`; local host numbers must not be treated as
  final device evidence.

## Evidence Snapshot

Branch-level commands/results from the audit:

- `git fetch --all --prune`: completed.
- `git status --short --branch`: current working tree had unrelated UI/testing
  changes, so clean branch evidence was reviewed in a detached worktree.
- `python scripts/validate_harness_fixture_parity.py`: passed on clean branch.
- `python -m unittest discover -s test\scripts -p "*_test.py"`: passed
  23 tests on clean branch.
- `python tools\validate_feature_spec.py --all`: passed `0 file(s)` in the
  clean detached branch, which means no branch-tracked feature flow files were
  discovered there.
- `python tools\validate_retired_flow_ids.py`: failed in the clean detached
  branch because `.claude/test-flows/flow-dependencies.md` was missing.
- `pwsh -File tools\supabase_local_reset.ps1`: failed during
  `supabase/seed.sql` with `column "header_data" is of type jsonb but expression
  is of type text`.
- Latest GitHub `gocr-integration` runs at `cffadc9e` failed for
  `.github/workflows/quality-gate.yml` and
  `.github/workflows/sentry-auto-issue.yml` before jobs/logs were created.
- Implementation pass local results on 2026-04-17:
  - Workflow YAML parse check passed for 7 workflow files.
  - `python scripts/validate_harness_fixture_parity.py`: passed.
  - `python scripts/validate_sync_adapter_registry.py`: passed.
  - `python tools\validate_feature_spec.py --all`: passed 16 feature files.
  - `python tools\validate_retired_flow_ids.py`: passed 115 indexed IDs.
  - `python -m unittest discover -s test\scripts -p "*_test.py"`: passed
    23 tests.
  - `pwsh -File tools\supabase_local_reset.ps1`: passed.
  - `flutter test test\harness\harness_sync_matrix_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true`:
    passed.
  - `flutter test test\harness\sync_performance_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true --dart-define=SYNC_PERF_RUNS=5`:
    passed with `coldFullMs=483`, `warmQuickMs=151`, `379` rows pulled.
  - `python scripts\check_perf_regression.py --baseline scripts\perf_baseline.json --actual build\perf\sync-performance.json`:
    passed.
  - `pwsh -File scripts\audit_ui_file_sizes.ps1`: passed after extracting
    `entry_activities_location_editor_list.dart`.
  - `flutter test test\features\entries\presentation\widgets\entry_activities_section_test.dart`:
    passed.
  - `flutter test test\harness\sync_defect_regressions_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true`:
    passed.

## Must Fix Before Any Final Dual-Device Run

- [x] Fix YAML parsing in `.github/workflows/quality-gate.yml`.
  - Current issue: the inline Python heredoc body under the lint auto-issue
    event generation block is not indented inside the YAML `run: |` block.
  - Acceptance: parse the workflow locally with a YAML parser and confirm the
    next GitHub push creates jobs instead of an empty failed run.
- [x] Fix YAML parsing in `.github/workflows/sentry-auto-issue.yml`.
  - Current issue: the inline Python heredoc body under the normalize/apply step
    is not indented inside the YAML `run: |` block.
  - Acceptance: parse locally and confirm the workflow can be dispatched or
    triggered without a pre-job parse failure.
- [x] Fix `supabase/seed.sql` so `form_responses.header_data` is inserted as
  `jsonb`, not text.
  - Current failure: local reset dies on `header_data` type mismatch.
  - Acceptance: `pwsh -File tools\supabase_local_reset.ps1` passes from a clean
    branch checkout.
- [x] Pass `HARNESS_SUPABASE_PASSWORD` into the quality-gate 10-minute staging
  soak step.
  - Current mismatch: `HarnessAuthConfig` rejects staging URLs that use the
    local default `HarnessPass!1`, but `quality-gate.yml` does not pass the
    staging password into the soak step.
- [x] Pass `HARNESS_SUPABASE_PASSWORD` into the quality-gate staging sync
  performance step.
  - Acceptance: quality-gate soak and perf use staging URL, staging anon key,
    and staging-only harness password without exposing service-role keys to
    Flutter runtime.
- [x] Re-run clean-branch script gates after the above fixes:
  - `python -m unittest discover -s test\scripts -p "*_test.py"`
  - `python scripts\validate_harness_fixture_parity.py`
  - `python scripts\validate_sync_adapter_registry.py`
  - workflow YAML parse check for all `.github/workflows/*.yml`
- [ ] Re-run local Docker harness gates after seed reset is repaired:
  - `pwsh -File tools\supabase_local_reset.ps1`
  - `flutter test test\harness\harness_sync_matrix_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true`
  - `flutter test test\harness\sync_performance_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true`
  - `pwsh -File scripts\soak_local.ps1 -DurationMinutes 10 -UserCount 20 -Concurrency 8 -ActionDelayMilliseconds 250`
  - Status: reset, matrix, performance, and hardened concurrent backend/RLS
    soak passed. The soak result was `attemptedActions=12368`,
    `actions=12368`, `failedActions=0`, `errors=0`, `rlsDenials=0`,
    `concurrentWorkers=8`, `virtualUsers=20`.

## UI E2E Feature Harness Gaps

Spec/prompt verdict:

- The UI E2E spec captured the S21/S10 feature-harness intent well, including
  feature files, scenario-DAG seeding, forward/back/deep-link/nav-switch
  coverage, role/device matrix, sentinel keys, and screen contracts.
- The original prompt also asked for Windows build navigation coverage. The UI
  E2E spec explicitly deferred Windows, so the spec does not fully capture the
  complete original prompt.

Branch gaps:

- [x] Ensure `.claude/test-flows/features/*.md` are branch-tracked if they are
  intended to be part of the deliverable.
  - Clean branch audit found no feature files in the detached worktree.
  - Live working tree had feature files, but those were not clean-branch
    evidence.
- [x] Ensure `.claude/test-flows/flow-dependencies.md` is branch-tracked or
  update `tools/validate_retired_flow_ids.py` to point at the branch-tracked
  replacement.
  - Current clean-branch result: validator fails with `missing_index`.
- [x] Run and pass `python tools\validate_feature_spec.py --all` with non-zero
  feature count.
- [x] Run and pass `python tools\validate_retired_flow_ids.py`.
- [x] Run and pass `pwsh -File scripts\audit_ui_file_sizes.ps1`.
  - Prior live-tree reviewer found `entry_activities_section.dart` over the
    300-line ceiling; recheck on the current committed branch after the working
    tree commit lands.
- [ ] Confirm all root/screen sentinels are visible through real screen
  contracts, not only declared keys.
- [ ] Finish a full S21/S10 manual UI sweep after static gates pass.
  - Must cover forward and backward navigation through all feature flows.
  - Must use real sessions, screenshots/logs/sync state where relevant.
  - Must not use `MOCK_AUTH`.
- [ ] Add a future Windows UI/navigation plan or explicit spec amendment.
  - Current Phase 1 intentionally excludes Windows.

## Sync/Auth/Role Hardening Gaps

Spec/prompt verdict:

- The sync hardening spec captured most of the prompt: local Docker Supabase,
  staging, seeded multi-role personas, RLS/role matrix, five named defects,
  property tests, soak tests, performance gates, Sentry/log drains, and GitHub
  auto-issue policy.
- It explicitly excluded multi-account-on-one-device session switching, even
  though the user prompt raised it as a concern. Track that as a separate
  follow-up unless the spec is amended.

Branch gaps:

- [x] Fix the clean local Docker reset seed failure.
- [x] Reconcile `harness_sync_matrix_local_test.dart` with the expanded fixture.
  - Reviewer noted stale expectations around `form_responses` after the branch
    added entry-linked form responses.
- [x] Replace synthetic/failing-by-construction defect repros with real
  regression tests.
  - `download_on_click_test.dart` and `flashing_repro_test.dart` were flagged
    as simulated rather than real fixed-behavior proof.
  - Status: replaced the simulated integration tests with local Supabase
    harness assertions and added host-runnable
    `test\harness\sync_defect_regressions_local_test.dart` for the same
    project-leakage/download-graph regressions.
- [x] Re-run the matrix against the expanded fixture after reset is fixed.
- [x] Re-run local performance proof against the expanded fixture.
- [x] Update `scripts/perf_baseline.json` only after the expanded fixture
  performance proof is accepted.
- [x] Re-run local 10-minute Docker soak after the expanded fixture reset
  passes.
  - Clarification: this is a local Supabase backend/RLS action-mix soak. It is
    useful, but it does not replace real S21/S10 sync measurements or a
    device/app `change_log` soak.
  - Status: passed hardened concurrent profile on 2026-04-17 with 8 concurrent
    workers, 20 virtual users, 12,368 verified actions, 0 failed actions, and 0
    RLS denials.
- [ ] Add/prove a separate device/app soak that exercises local SQLite
  `change_log`, real app sessions, and UI-triggered sync on S21/S10.
  - The backend/RLS soak cannot satisfy this by design because it talks directly
    to Supabase.
  - Status: added `test\harness\soak_driver_app_test.dart` and changed the
    driver soak executor to trigger sync through the Sync Dashboard UI button.
    Still needs real-device execution/artifacts on S21/S10.
- [ ] Reframe the current `12k` soak result as backend/RLS evidence only.
  - Research/audit finding: the passed 12,368-action run is plausible because
    the headless path signs in multiple Supabase clients and mutates remote
    rows directly. It does not generate local SQLite `change_log` rows, contend
    on `sync_lock`, run `SyncEngine.pushAndPull`, upload/download file bytes, or
    prove device queue drainage.
  - Acceptance: docs, plan language, CI job names, and artifact names make the
    distinction clear: `backend_rls_soak` is not `device_sync_soak`.
- [ ] Build an enterprise device-sync soak lane that stresses the exact failure
  surface seen on S21/S10.
  - Must launch at least two driver apps/ports for S21 + S10, not one process
    with 20 backend clients.
  - Must create local app changes that write SQLite `change_log` through real
    local data paths, then trigger sync through the Sync Dashboard UI button.
  - Must assert before/after `pendingCount`, `blockedCount`, `unprocessedCount`,
    per-table `change_log` samples, `lastSyncTime`, and local record state on
    every device actor.
  - Must fail on any blocked rows, retry-count growth, stale lock, unchanged
    `lastSyncTime`, runtime sync error, screenshot/UI defect, or unauthorized
    project visibility.
- [ ] Expand the device soak action mix beyond the current backend action mix.
  - Missing today: real photo/file byte upload, storage-object download proof,
    `storage_cleanup_queue`, form responses, signatures, documents/export
    artifacts, pay-app/export artifacts, support/consent rows, large payloads,
    and project download/import graph assertions.
  - Missing today: app logout/login/session rebinding and multi-account on the
    same physical device.
  - Missing today: multi-device same-project conflict/pull behavior, remote
    actor mutations while devices are syncing, and assignment revocation while
    screens are open.
- [ ] Add failure injection to the enterprise soak.
  - Must cover offline/online transitions, timeout/socket failures, expired or
    refreshed auth sessions, Supabase rate-limit/transient errors, storage
    upload failure after local queue creation, app background/foreground, and
    process restart mid-sync.
  - Must verify retry/backoff, blocked-row classification, repair visibility,
    and eventual queue drain after the injected condition clears.
- [ ] Scale the fixture to field-like payload size before treating soak as
  stress evidence.
  - The current seed is useful for role/RLS matrix checks, but it is too small
    for device storage, SQLite WAL/checkpoint, image bytes, and large first-sync
    behavior.
  - Acceptance: fixture includes 15 projects, 10-20 active users, realistic
    entry counts, real-size images/documents/signatures, export artifacts, and
    overlapping same-project edits.
- [ ] Promote CI/staging soak language and artifacts to two explicit layers.
  - `backend_rls_soak`: Docker/staging Supabase concurrency, RLS, RPCs, direct
    remote CRUD, server-side metrics.
  - `device_sync_soak`: local SQLite/change_log, UI-triggered sync, device
    storage, local queue, auth/session rebinding, realtime hints, screenshots,
    logs, and S21/S10 artifacts.
- [ ] Provision or confirm dedicated staging Supabase.
- [ ] Seed staging with deterministic harness data and staging-only password.
- [ ] Prove staging sign-in for at least admin and inspector harness personas.
- [ ] Confirm local/staging schema hash parity with `scripts/hash_schema.py`.
- [ ] Run the 10-minute staging soak from GitHub and upload metrics.
- [ ] Run the staging performance gate from GitHub and upload metrics.
- [ ] Run the 15-minute nightly staging soak from GitHub and upload metrics.
- [ ] Collect three consecutive green 10-minute staging soaks.
- [ ] Collect three consecutive green 15-minute nightly soaks.
- [ ] Run real-device full-sync timing on S21 with
  `tools\measure-device-sync.ps1` after launching the driver app.
- [ ] Run real-device full-sync timing on S10 tablet with
  `tools\measure-device-sync.ps1` after launching the driver app.
- [ ] Confirm both device artifacts were triggered through the UI and did not
  use `POST /driver/sync`.
- [ ] Verify Supabase Log Drains into Sentry for `postgres_logs`, `auth_logs`,
  and `edge_logs`.
- [ ] Run or otherwise prove
  `deno test supabase/functions/_shared/log_drain_sink.test.ts`.
- [ ] Configure and prove Sentry `repository_dispatch` into
  `.github/workflows/sentry-auto-issue.yml`.
- [ ] Prove fatal/error events create or update issues with hashed identifiers
  only, and warning events stay digest-only.
- [ ] Confirm all five sync ship-bar conditions at the same commit:
  correctness matrix green, five named defects fixed, staging soak stable,
  staging full sync under 2 seconds, and observability/auto-issue pipeline live.
- [ ] Create a separate follow-up for multi-account-on-one-device switching if
  still required by product intent.

## Android Codemagic/Firebase CI/CD Gaps

Plan/prompt verdict:

- The Android Codemagic/Firebase plan captures the selected model: GitHub
  quality gates, GitHub beta tags as the human release switch, Codemagic as the
  tester-build/distribution system, and Firebase App Distribution as the Android
  TestFlight equivalent.
- If "single CI/CD pipeline" means all validation must move into Codemagic,
  this plan only partially captures that. If it means one tester-distribution
  pipeline, it captures the intent.

Branch-confirmed wiring:

- `codemagic.yaml` defines `android-firebase`.
- `android-firebase` triggers on `field-guide-beta-v*` tags.
- Android Firebase config is restored from
  `ANDROID_GOOGLE_SERVICES_JSON_B64`.
- Runtime/publishing secrets are checked before build.
- Release APK is built with `--build-name` and `--build-number`.
- Firebase App Distribution publishes to app id
  `1:860372996401:android:157920afc316bffc962010`.
- Tester group alias is `field-guide-android-testers`.
- Android CI release signing fails when Codemagic signing is missing.

Remaining confirmation work:

- [ ] Fix GitHub workflow YAML blockers first; current branch CI is not green.
- [ ] Confirm Codemagic can see the branch workflow config after the next push.
- [ ] Confirm required Codemagic environment groups/secrets exist:
  - `android_firebase`
  - `firebase_distribution`
  - `ANDROID_GOOGLE_SERVICES_JSON_B64`
  - `FIREBASE_SERVICE_ACCOUNT`
  - Android keystore reference `field-guide-android-upload`
  - `supabase_credentials`
- [ ] Confirm Firebase App Distribution tester group
  `field-guide-android-testers` exists and has testers.
- [ ] Push a real beta tag using
  `field-guide-beta-v<version>+<build>`.
- [ ] Confirm Codemagic starts `android-firebase` from that tag.
- [ ] Confirm Codemagic starts `ios-testflight` from that same tag if the
  coordinated beta release model is still intended.
- [ ] Confirm Android signed APK artifact is produced.
- [ ] Confirm Firebase receives the APK.
- [ ] Confirm at least one tester can install the Firebase App Distribution
  build.
- [ ] Record Codemagic build URL, Firebase release proof, tag, commit SHA, and
  tester-install proof in the active release tracker.

## Final Device Run Prerequisites

Do not start final dual-device signoff until all of these are true:

- [x] GitHub workflow YAML parse blockers fixed.
- [ ] Latest `gocr-integration` GitHub quality gate starts jobs and completes.
- [x] Local Docker reset passes from clean branch state.
- [ ] Local matrix, local performance, and local 10-minute soak pass against
  the accepted fixture.
  - Reset, matrix, and performance pass; local soak still pending.
- [x] UI feature-flow validators pass with branch-tracked feature files.
- [x] Staging soak/perf credentials are correctly wired.
- [ ] At least one staging soak and one staging performance run pass.
- [x] Known stale/synthetic sync tests are repaired or explicitly replaced by
  real regression coverage.
- [ ] Real S21 and S10 full-sync timing artifacts exist under
  `.claude/test-results/<date>/device-sync-measurements/`.

After those prerequisites:

- [ ] Run S21 phone full UI/RLS/sync sweep with real sessions.
- [ ] Run S10 tablet full UI/RLS/sync sweep with real sessions.
- [ ] Cover admin, engineer, office technician, and inspector roles.
- [ ] Review screenshots, runtime logs, and sync state before marking any cell
  passed.
- [ ] Log all remaining defects to `.claude/test-results/` and update the
  relevant closeout tracker.
