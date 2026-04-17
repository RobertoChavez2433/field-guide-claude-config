# Sync System Hardening And Test Harness

**Work Type:** Refactor+ (+ Security Hardening, New Feature — test infrastructure)
**Date:** 2026-04-16
**Spec Author:** Paired conversation (Claude Opus 4.7 + user)

---

## Intent

**Problem:** Real users are now on the live Supabase, so the team can no longer iterate on sync by pushing changes and watching production. The current sync system exhibits role-visibility leakage (inspectors see projects they are not assigned to, including flashing metadata of unrelated projects on refresh), assignment propagation failures (new users not attached to existing projects), download-on-click failures, and a "snail pace" that makes the team fear breakage at user scale. The existing test coverage is deep on unit and characterization layers but has no cross-role, full-stack, concurrent-user proving ground that can be run before changes reach production. This initiative stands up that proving ground, uses it to reproduce and fix every known sync/role/RLS/assignment/download defect, threads a unified logging and observability pipeline through every sync-relevant mutation, rewrites sync hotspots (and architectural seams where hotspots are architectural) to hit a 2-second full-sync target, and makes a green harness run the permanent gate for any future sync-touching change.

**Who feels it:**
- Inspectors using the app in the field — currently experience flashing metadata, phantom projects, failed downloads, and slow sync.
- Admin and engineer users creating projects and assignments — currently see assignment propagation issues.
- The development team — currently lacks pre-production verification and real-user observability for sync failures.
- You as the operator — currently have no single pane to triage user-reported sync problems.

**Success criteria (measurable):**
1. All four role personas (admin, engineer, office_technician, inspector) pass a hand-written correctness matrix covering the full sync-adjacent feature surface — auth, projects, assignments, entries, photos, signatures, all four form types (0582B, 1174R, 1126, IDR), pay apps, quantities, equipment, contractors, personnel, locations, todos, consent, support, documents, exports — with zero cross-role visibility violations on any frame.
2. A property-based concurrency suite runs to completion with no invariant violations across generated scenarios.
3. A 10-minute CI soak test and a 15-minute nightly soak test both run green against a dedicated staging Supabase project, using a seeded fixture of ~10-20 users across multiple projects with a concurrent action mix of 30% reads, 30% entry mutations, 15% photo uploads, 20% deletes/restores, 5% role/assignment changes.
4. Cold-start full sync (empty SQLite, fresh auth, all tables) against staging completes in ≤ 2 seconds on the seeded fixture.
5. Foreground unblock on warm start ≤ 500ms; cold-start shows an empty-state within ≤ 500ms and fills in ≤ 2 seconds.
6. Per-PR performance regression gate blocks any change that pushes full-sync wall time above +10% of baseline or above the 2-second ceiling.
7. All five enumerated defects have deterministic failing repros committed to the harness as regression tests, each then passing after its fix: (a) inspector sees unassigned projects on refresh, (b) flashing metadata when a new project is created, (c) new-user-to-old-project assignment failure, (d) download-on-click failure, (e) single-account refresh bleed (inspector sees unassigned company projects).
8. A logging event-class audit (CodeMunch-assisted) reports zero gaps against the locked event-class list; a static audit script committed at `scripts/audit_logging_coverage.ps1` and run in CI walks sync, auth, and project-selection code and fails if any method in the must-log set lacks a log seam.
9. Sentry is wired as the single observability pane: client-side events from Flutter flow in; Supabase Log Drains forward `postgres_logs`, `auth_logs`, and `edge_logs` from the Pro-plan staging project; a five-layer filter (log-level, sampling, pre-Sentry dedup middleware, rate-limit, breadcrumb budget) keeps the Sentry client under 5,000 ingested error events per month on the seeded-fixture + nightly-soak workload.
10. Sentry → GitHub auto-issue pipeline is live and applies to all GitHub auto-filers in the project (not only Sentry): fingerprint grouping, rate limit of 1 issue per fingerprint per 24h, creation threshold of ≥2 distinct users or ≥5 occurrences in 15 minutes, auto-close after 7 days with zero new events, severity routing (`fatal` → immediate, `error` → threshold, `warning` → digest only), and a three-night stability period before the nightly soak is allowed to auto-file issues.
11. The hardened MVP ships to current pre-alpha users only when all five ship-bar conditions hold simultaneously: correctness matrix green, all five enumerated defects fixed, soak green, 2-second full-sync met, logging/Sentry/GitHub pipeline live.
12. The harness gate persists past this initiative: every future sync-touching PR must pass the correctness matrix, the property-based concurrency suite, and the 10-minute CI soak against staging before it can merge.

**Why now:** Real users are on the live Supabase for the first time, removing "iterate on prod" as a safe development pattern. The current sync system is already showing correctness and performance symptoms at pre-alpha scale (one real user), and adding more users without a hardening pass will multiply those symptoms. The forcing function is that the next hardening pass either happens through a proving ground built now, or through live-user incident response later.

---

## Scope

### In scope (v1)

- Local Docker Supabase harness boot, seeded with ~10-20 users across multiple projects, applying current migrations and seed data.
- Full-feature correctness matrix across every sync-adjacent flow (enumerated above in Success criterion 1).
- Role/RLS correctness invariants for all four roles (admin, engineer, office_technician, inspector) and the deprecated-viewer fallback path.
- Property-based concurrency tests using `glados` as the default library, with a table-driven fallback when `glados` cannot express an invariant cleanly within a time-boxed effort.
- Soak test driver supporting configurable duration (5 / 10 / 15 minutes), 20 virtual users, weighted action mix (30% reads, 30% entry mutations, 15% photo uploads, 20% deletes/restores, 5% role/assignment changes).
- Dedicated staging Supabase project on the Pro plan ($25/month); migration-promotion rule that blocks prod migration on any commit not already applied cleanly on staging; CI schema-hash gate comparing local / staging / prod; reset-and-seed sequence run as a single job at the start of each nightly.
- Logging event-class audit and implementation. Locked must-log event classes: every `SyncEngine` public method entry/exit/thrown error; every `change_log` row write, trigger fire, rollback; every RLS denial (SQLSTATE `42501`) caught client-side; every `project_assignments` mutation; every auth state transition (sign-in, sign-out, token refresh, session expire, role change); every pull-scope enrollment and teardown; every realtime hint emit/receive/consume; every download-on-click initiate/complete/fail; every conflict resolution decision (LWW winner, clock-skew fallback); every FK-rescue action; every Edge Function call (request, response, error); every retry policy decision (retry, escalate, give-up). The list is allowed to grow during both audit and implementation when additional log-worthy paths are discovered.
- Sentry client-side SDK integration with five-layer noise filter: log-level filter (only `warning` / `error` / `fatal` forwarded); event sampling at 5-10% for high-volume non-error classes; pre-Sentry dedup middleware with a 60-second fingerprint buffer; rate limit of 50 events/user/day; breadcrumb budget of 30 per event.
- Supabase Log Drains configured on the staging Pro project, forwarding `postgres_logs`, `auth_logs`, `edge_logs` into Sentry.
- Sentry → GitHub auto-issue pipeline with full noise policy (fingerprint grouping, rate limit 1/fingerprint/24h, creation threshold ≥2 users or ≥5 occurrences in 15 min, auto-close after 7 days with zero new events, severity routing, three-night stability period before nightly soak auto-issue activates). Noise policy applies to **all** GitHub auto-filers in the project, not only Sentry.
- In-app "Report a problem" flow that captures a Sentry event with recent logs, user id, project id, device info.
- Sync engine rewrite: targeted hotspot rewrite (parallel table pulls, change_log cursor advancement, pull-scope enrollment, realtime-hint fan-out, and other candidates identified by profiling against the seeded fixture) with selective architectural tightening where the hotspot itself is architectural. Adapter registry, custom lint rules, CI drift validator (`scripts/validate_sync_adapter_registry.py`), and `SyncCoordinator` as the single sync entrypoint are preserved. Escape clause: if profiling against the seeded fixture demonstrates the architecture itself blocks the 2-second ceiling and targeted + selective rewrite cannot clear it, C-depth rewrite (contract changes allowed) is authorized without reopening Scope.
- Flashing-fix implementation posture: apply the assignment filter pre-first-render so the UI never renders an unfiltered project list; no skeleton-then-filter fallback pattern.
- Concurrent-mutation source of truth for cross-role visibility: RLS (hard boundary) + client-side filter (defense-in-depth for the server-to-client propagation window). Both layers hold the invariant; neither alone is sufficient.
- Sentry silent-failure definition: "zero silent failures" means error-class failures are fingerprint-visible in Sentry. Sampled breadcrumbs, rate-limited duplicates, and info-level logs are by design local-only and are not considered silent failures.
- Local developer soak utility (`scripts/soak_local.ps1`) usable ad-hoc during sync refinement work; runs against the local Docker Supabase; not a gate.
- Sequencing is strict, single-track, safety-first (Execution Option 1): local Docker Supabase and seeded fixture → harness skeleton → full-surface correctness matrix → logging event-class audit + Sentry dual-feed integration → property-based concurrency + soak → targeted (and if necessary architectural) sync engine rewrite → staging Supabase project + CI gate + full noise policy live.
- MVP ship-bar is conjunctive: all five conditions from Success criterion 11 must hold before shipping to the pre-alpha users.
- Existing characterization / unit / widget test suites coexist with the new harness by default. A characterization test is deleted only if the harness proves the same contract in a more honest way.

### Deferred (not v1, not out of scope forever)

- Deeper full-system sync rewrite informed by live user telemetry captured by the new Sentry + GitHub pipeline. The hardened MVP is the baseline from which the deeper rewrite is later scoped.
- Numeric perf SLOs beyond the 2-second ceiling and +10% regression gate (p95 / p99 latency contracts, throughput-per-minute targets, realtime-hint delivery SLOs).
- Soak action-mix recalibration once real telemetry exists to measure the true field-inspector load shape. Locked at 30/30/15/20/5 for v1.
- Ephemeral Supabase project per PR (highest fidelity, highest cost). Remains available but not adopted in v1.

### Out of scope

- Multi-account-on-one-device session switching (two users signing in and out on the same device without state bleed).
- OCR improvements: Google Vision Edge Function tuning, OCR quality gates, extraction corpus changes.
- PDF extraction and PDF generation improvements beyond what the sync engine exposes — form fidelity, column auto-fill, font and alignment work stays in its own lane.
- UI redesign beyond render-ordering fixes needed for flashing. No broader visual redesign.
- Auth flow UX changes: no changes to OTP, email or SMS verification, company-join UI, profile-setup flow. RLS and role logic are in; UX is out.
- New features and new form types: no MDOT 1126 or IDR redesign, no new form types, no new calculators.
- Numeric perf SLOs beyond the 2-second ceiling and +10% regression gate.
- Cross-repo or cross-service changes: Codemagic configuration, Firebase App Distribution, release tooling, signing keys stay as-is.
- Enterprise-sync research that does not produce code. Research is allowed but deliverables are sync behavior and tests, not tech-selection documents.
- Pre-existing test suite overhaul. Existing characterization / unit / widget tests stay; consolidation happens only if the harness makes a specific test honestly redundant.

### Constraints

- Live production Supabase is off-limits for iteration for the duration of this initiative. All sync development and verification happens against local Docker or staging.
- Offline-first remains the default: local SQLite is the client's source of truth; sync is a background concern.
- `change_log` is trigger-owned; no direct inserts from client code.
- Soft delete is the default; hard delete stays explicit.
- `is_builtin=1` rows are server-seeded and retain existing skip behavior.
- `SyncCoordinator` remains the single sync entrypoint.
- `SyncErrorClassifier` continues to own sync error classification.
- `SyncStatus` remains the single source of truth for transport state.
- No reintroduction of `sync_status` columns or indexes.
- RLS stays company-scoped via `get_my_company_id()`; no user-scoped policy fallbacks.
- `change_log` child-table RLS continues to derive scope through the parent chain until it reaches `company_id`.
- `42501` (RLS denial) is treated as a real security-boundary failure, not a retryable sync hiccup.
- PowerShell wrappers are used for all Flutter and Dart commands; Flutter is not invoked directly from Git Bash.
- `flutter analyze` and `dart run custom_lint` stay green throughout the initiative.
- Existing custom lint rules (`push_handler_requires_sync_hint_emitter`, `no_sync_hint_rpc_outside_approved_owners`, `no_sync_hint_broadcast_subscription_outside_realtime_handler`, `no_client_sync_hint_broadcast_http`, `max_ui_callable_length`, `max_ui_file_length`, `screen_registry_contract_sync`) remain enforced.
- Testing follows `rules/testing/testing.md`: real behavior over mock presence; no test-only methods or lifecycle hooks on production classes; `TestingKeys` not hardcoded `Key('...')`.
- Sync-visible UI stays inspectable through the existing driver contracts (`screen_registry`, `screen_contract_registry`, `flow_registry`, `driver_diagnostics_handler`, `/diagnostics/screen_contract`); any screen-contract change updates the driver registry, contract registry, flows, and targeted tests in the same change.
- The Sentry client remains on the free tier (5k errors/month, 10k performance events, 1 team member) via the five-layer filter.
- Supabase staging runs on the Pro plan to enable native Log Drains.

### Non-goals

- Multi-account-on-one-device session switching.
- OCR improvements: Google Vision Edge Function tuning, OCR quality gates, extraction corpus changes.
- PDF extraction and PDF generation work beyond what the sync engine exposes.
- UI redesign beyond render-order fixes for flashing.
- Auth flow UX changes.
- New features or new form types.
- Numeric perf SLOs beyond the 2-second and +10% gates.
- Cross-repo or release-tooling changes.
- Enterprise-sync research that does not produce code.
- Pre-existing test suite overhaul beyond consolidation-on-demand.

---

## Vision

**User journey:**
1. An inspector opens the Field Guide app on their device.
2. The foreground unblocks within 500ms on warm start, or shows an empty-state placeholder within 500ms on cold start and fills in within 2 seconds.
3. The project list renders with only the projects the inspector is assigned to — the assignment filter has already been applied before first render. No unfiltered list frame is ever shown.
4. The inspector pulls to refresh. No phantom projects appear for any duration, not even a single frame. Metadata for projects the inspector is not assigned to never flashes.
5. The inspector taps a project to download it. The download starts immediately and completes reliably.
6. The inspector performs their day's work — entries, photos, signatures, forms, pay-app edits — and sync happens silently in the background.
7. If a sync operation fails, the inspector either sees a clear actionable message (if the failure is user-resolvable) or nothing at all (if the failure is operational, in which case the team sees it via Sentry and a GitHub issue, and the failure is reproducible in the harness by replaying the captured trace).
8. The operator (you) receives GitHub issues for deduped, rate-limited, threshold-qualified sync errors, each linked to a Sentry trace with fingerprint, breadcrumbs, and device context. The nightly soak's Monday-morning result tells you whether sync regressed over the weekend.

**Key interactions:**
- Pull-to-refresh on the project list never shows unfiltered data, never shows phantom projects, never shows flashing metadata.
- Download-on-click starts reliably and completes.
- Sign-out clears all relevant provider state; the next sign-in starts from a clean slate with no residue from the prior user on the same device.
- Admin creates a project and assigns an inspector; the inspector's client sees the new project only after the assignment has propagated, via either RLS enforcement or client-side filtering (defense-in-depth across both layers).
- Every sync-touching PR goes through the local Docker harness, the correctness matrix, the property-based concurrency suite, and the 10-minute CI soak against staging before it can merge.

**Acceptance-by-feel:**
- Users experience sync as invisible: no flashing, no waits, no phantom projects, no silent failures they would ever notice.
- The team experiences sync as fully observable: every error appears in Sentry with a fingerprint, every noise-qualified error becomes a GitHub issue, every failure is reproducible in the harness.
- The pre-alpha user's next report is "the app just works now" rather than another flashing-or-leakage defect.
- Every future sync-touching PR is gated before it reaches production; no sync regression is discovered in prod that the harness could have caught.
- You can triage user-reported sync problems from a single pane (Sentry) with a single issue trail (GitHub), without reaching into live Supabase logs manually.

---

## Pain Point

The current sync system exhibits role-visibility leakage (inspectors seeing unassigned projects, flashing metadata of unrelated projects on refresh), assignment propagation failures (new users not attached to existing projects), download-on-click failures, and a "snail pace" that the team fears will break under realistic user load. The existing test coverage — deep at the unit and characterization layers — cannot reproduce these defects deterministically, cannot simulate 10-20 concurrent users, and runs only against mocked or in-memory dependencies. Real users are now on the live Supabase, so the previous "push and watch" development pattern is no longer acceptable. The team lacks a pre-production proving ground that exercises real RLS, real triggers, real RPCs, and real concurrent client behavior, and lacks a unified observability pipeline that surfaces sync failures from live users back to the team in a single pane.

## Target Shape

A harness-gated hardened sync system: a local Docker Supabase proving ground plus a dedicated staging Supabase project on the Pro plan, driven by a full-stack harness that exercises real RLS, real triggers, real RPCs, and the real Flutter sync client against a seeded fixture of ~10-20 users across multiple projects. The harness runs a hand-written correctness matrix across every sync-adjacent feature surface, a property-based concurrency suite, and 5 / 10 / 15-minute soak tests with a weighted action mix. A unified observability pipeline threads Sentry through every sync-relevant mutation, with Supabase Log Drains feeding server-side signals in and a deduped, rate-limited GitHub auto-issue pipeline with comprehensive noise policy feeding operator triage out. The sync engine is rewritten where profiling identifies hotspots (targeted) or where the architecture itself is the hotspot (selective tightening), preserving adapter registry, lint rules, drift validator, and `SyncCoordinator` entrypoint, with an escape clause allowing deeper C-depth rewrite if profiling proves it necessary. The hardened MVP ships to pre-alpha users when all five ship-bar conditions hold. The harness gate persists past this initiative: every future sync-touching PR must pass correctness matrix + property-based concurrency + 10-minute CI soak before merge.

## Ambition Level

**Option:** Whole subsystem.
**Why this over the others:** The initiative spans the sync engine (targeted and possibly architectural rewrite), the full sync-adjacent feature surface (correctness matrix across ~20 feature areas), auth/RLS (role-visibility hardening), the observability layer (logging event-class audit, Sentry client + server feeds, GitHub auto-issue pipeline, noise policy), the test infrastructure (local Docker Supabase, staging Supabase project, property-based tests, soak driver), and CI (schema-hash gate, soak-on-merge, drift validators). A single-class or minimum refactor would be unable to deliver any of the three non-negotiable Vision qualities (zero cross-role visibility, zero visible sync wait, zero silent failures) because each quality requires coordinated changes across multiple subsystems.
**Phase scope:** this spec covers the full MVP hardening pass in a single phase, executed via Option 1 sequential single-track. A deeper full-system sync rewrite driven by live user telemetry is explicitly deferred to a later spec.

## Blast Radius Budget

- **Files touched:** cap not specified as a hard number; expected to span `lib/features/sync/**`, `lib/features/auth/**`, `lib/features/projects/**`, `lib/features/entries/**`, `lib/features/forms/**`, `lib/features/pay_applications/**`, `lib/features/quantities/**`, `lib/features/photos/**`, `lib/features/todos/**`, `lib/features/support/**`, `lib/features/consent/**`, `lib/core/driver/**`, `lib/core/logging/**`, `supabase/migrations/**`, `supabase/seed.sql`, `scripts/**`, `.github/workflows/**`, `codemagic.yaml` (observability wiring only), and `test/**`. The Scope's constraints and existing CI drift validators bound behavioral changes.
- **Behavior changes allowed:** yes, within Scope. Sync engine internals may change substantially; role-visibility enforcement may gain a defense-in-depth client filter layer; logging is introduced to every event-class path. Contract preservation rules: adapter registry, custom lint rules, CI drift validator, `SyncCoordinator` entrypoint, `SyncErrorClassifier` ownership, `SyncStatus` authority are preserved unless the escape clause is invoked by profiling evidence.
- **Rollback strategy:** multi-PR. Each sequential phase (harness skeleton, correctness matrix, logging audit, Sentry integration, PBT/soak, rewrite, staging/CI) lands as one or more focused PRs that can be reverted independently. The hardened MVP ships to pre-alpha users only after all five ship-bar conditions hold; if a post-ship regression is detected, the culprit PR is reverted rather than the whole initiative.

## Test Coverage Floor

- Local Docker Supabase boots cleanly from current migrations and `supabase/seed.sql`, with a seeded fixture of ~10-20 users across multiple projects, before any correctness work begins.
- Harness driver skeleton can authenticate as any of the four roles, drive the real Flutter client, and assert against real RLS responses, before any matrix authoring begins.
- Every enumerated defect (5 items in Success criterion 7) has a failing repro committed to the harness before its fix is attempted.
- Correctness matrix covers every feature area listed in Success criterion 1 with invariants for every role and every CRUD direction, before logging audit work begins.
- Logging event-class audit produces a written report of coverage against the locked must-log list, with gaps enumerated, before Sentry client wiring begins.
- Sentry client integration includes all five filter layers (log-level, sampling, dedup, rate-limit, breadcrumb budget) before any event is forwarded to the Sentry project.
- Supabase Log Drains are verified forwarding `postgres_logs`, `auth_logs`, and `edge_logs` from the staging project into Sentry before the staging CI gate is declared live.
- Property-based concurrency suite passes on the local harness before being added to CI.
- 10-minute soak runs green for three consecutive CI runs before being declared the pre-merge gate.
- Nightly 15-minute soak runs green for three consecutive nights before it is allowed to auto-file GitHub issues.
- Existing characterization / unit / widget test coverage remains green throughout; no test is deleted unless the harness proves the same contract more honestly.

## Open Questions / Deferred to Tailor

- Specific file targets for each sequential phase (which existing files are touched vs. which new files are created) — to be mapped during `/tailor`.
- Exact `glados` integration patterns for the sync engine's async / provider layer — to be discovered during the PBT phase and documented as part of implementation.
- Profiling methodology details (which tool, which fixture size, which measurement methodology for cold-start-to-staging) — to be specified at the start of the sync-engine rewrite phase.
- Which specific Supabase Log Drain sink format is used (Logflare, Datadog, custom HTTP webhook to Sentry) — to be specified during the Sentry dual-feed integration phase.
- Concrete noise-policy fingerprint rules per event class (RLS denials grouped by `{table, policy_name}`, retry exhaustion grouped by `{adapter, error_code}`, etc.) — to be specified during the Sentry integration phase.
- Delivery mechanism to pre-alpha users (TestFlight, App Distribution, forced update, on-device data reconciliation) — explicitly handled outside this spec after the ship-bar holds.
