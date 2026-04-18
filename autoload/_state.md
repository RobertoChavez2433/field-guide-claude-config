# Session State

**Last Updated**: 2026-04-18
**Branch**: `gocr-integration`
**Status**: The active lane is S21-first sync soak harness hardening using `.codex/plans/2026-04-17-s21-soak-harness-audit-and-recovery-plan.md` as the working spec. The refactored state-machine harness under `tools/sync-soak/` now has green S21 isolated gates for `sync-only`, `daily-entry-only`, `quantity-only`, and `photo-only`. Quantity and photo each have three accepted S21 passes with `passed=true`, `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`, `queueDrainResult=drained`, `blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`. Photo also proves Supabase Storage object download, ledger-owned cleanup, storage delete, and storage absence. S10, emulator, headless app-sync, backend/device overlap, and 15-20 user scale-up remain parked until the refactored S21 `combined` flow is implemented and green. The older pay-app XLSX S21 proof and CodeMagic/iOS state remain valid background context, but they are not the current active lane.

## Current State

- PR `#249` merged the UI design-system refactor, including the 300-line presentation ceiling enforced by `scripts/audit_ui_file_sizes.ps1`.
- Sync-driving UI now has explicit contracts through:
  - `lib/core/driver/screen_registry.dart`
  - `lib/core/driver/screen_contract_registry.dart`
  - `lib/core/driver/flow_registry.dart`
  - `lib/core/driver/driver_diagnostics_handler.dart`
- `/diagnostics/screen_contract` is the unified sync-facing UI inspection endpoint.
- Screen-local controller composition now lives in `di/*screen_providers.dart` files across auth, entries, forms, projects, quantities, settings, dashboard, pay applications, and similar refactored features.
- CI now enforces sync adapter drift with `scripts/validate_sync_adapter_registry.py` against `sync_engine_tables.dart`, `simple_adapters.dart`, and `sync_registry.dart`.
- The legacy `BaseRemoteDatasource` sync bypass has been removed; the remaining sync work is proof breadth, not major leftover executor cleanup.
- Foreground private-channel hints are now live-proven through the owned split:
  - `RealtimeHintHandler` owns subscribe / refresh / consume
  - `SyncHintRemoteEmitter` owns push-side `emit_sync_hint(...)`
  - `sync_hint_subscriptions` is the active-channel source of truth
- New custom lint now explicitly guards:
  - `push_handler_requires_sync_hint_emitter`
  - `no_sync_hint_rpc_outside_approved_owners`
  - `no_sync_hint_broadcast_subscription_outside_realtime_handler`
  - `no_client_sync_hint_broadcast_http`
- Current live proof checkpoint is `complete` after closing:
  - delete / restore / hard-delete / revocation
  - remove-from-device / fresh-pull parity
  - file-backed create/delete/cleanup
  - integrity / maintenance
  - support-ticket and consent live flows
  - retry/restart chaos matrix
  - quick-resume and realtime-hint mode proof
  - global full sync
  - dirty-scope isolation
  - private channel register/teardown
  - final mixed-flow soak
- Google Cloud Vision OCR prerelease status:
  - remote `google-cloud-vision-ocr` Edge Function is active
  - direct Flutter/client code is lint-blocked from owning Vision calls
  - company OCR mode is server-guarded by `company_app_config`
  - full Google OCR readiness now passes
- Pay-app export / analytics / tablet UI status:
  - `.codex/plans/2026-04-13-pay-app-export-tablet-analytics-spec.md` is the current working spec
  - saved pay apps are selectable from the pay-app export UI
  - saved pay-app XLSX copies export through Android DocumentsUI instead of the in-app summary screen
  - S21 proof pulled `/sdcard/Download/pay_app_5_2026-04-12_2026-04-18 (1).xlsx` and verified it as a valid XLSX containing `Springfield DWSRF`, `Mobilization`, `Pre-Construction`, `Video Survey`, and the `Quantities` sheet
  - Microsoft Excel opened the second visible S21 copy and showed document title `pay_app_5_2026-04-12_2026-04-18 (1)` with `Quantities` selected
- S21 sync-soak harness status:
  - `tools/enterprise-sync-soak-lab.ps1 -Flow sync-only` is green on S21 through the refactored state-machine path
  - `-Flow daily-entry-only` is green on S21 with ledger restore and exact local/remote cleanup sentinels
  - `-Flow quantity-only` is green on S21 with three accepted passes and ledger-owned soft-delete cleanup
  - `-Flow photo-only` is green on S21 with three accepted passes, storage download proof, storage delete proof, and storage absence proof
  - the next implementation gate is refactored `combined`; the CLI currently declares it but fails closed by design
  - do not restart S10/S21 concurrent runs or 15-20 user scale-up until combined S21 is green

## Quality Gates

- `flutter analyze` must stay clean.
- `dart run custom_lint` must stay clean.
- `scripts/audit_ui_file_sizes.ps1` must stay green.
- `python scripts/validate_sync_adapter_registry.py` must stay green.
- No ignore comments, analyzer excludes, or severity downgrades are permitted to bypass the lint gates.

## New Architecture Enforcement

Custom lint now explicitly enforces:
- `max_ui_callable_length`
- `max_ui_file_length`
- `screen_registry_contract_sync`

Existing rules still enforce:
- single composition roots
- no business logic in DI
- no datasource imports in presentation
- design-system widget/token usage

Cross-file sync drift is now guarded in CI by:
- `scripts/validate_sync_adapter_registry.py`

## Resume Priorities

1. Implement the refactored S21 `combined` flow in the state-machine harness without falling back to legacy `-UiMutationModes`.
2. Prove combined S21 green with strict log/runtime gates, ledger cleanup, storage proof, final empty queue, and no direct `/driver/sync`.
3. Only after combined S21 is green, reintroduce S10 as a regression device; keep emulator/headless app-sync/backend-device overlap/15-20 scale-up parked until then.
4. Keep Google OCR admin/company opt-in only; do not put the Google key in Flutter env/client code and do not reintroduce `codex-admin-sql`.

### Session 755 (2026-04-12, Codex)
**Work**: Implemented and live-proved Google Cloud Vision OCR via the Supabase Edge Function: added server-side company opt-in/auth checks, sanitized provider errors, tightened the direct-Google lint rule, added Edge Function contract tests, set the Supabase Google key secret, applied the missing remote OCR config table/RPC SQL, fixed Google billing/key restrictions, deployed the function, and deleted the remote `codex-admin-sql` debug function.
**Decisions**: Cloud OCR remains admin/company opt-in and defaults through `auto`; Google credentials stay server-side in Supabase secrets; Flutter code may only use the approved OCR adapter; direct Google and Edge Function smoke tests are valid setup proof, while corpus extraction quality still requires the standard PDF hardening harness.
**Next**: Resume prerelease work at PDF corpus hardening: run the new PDFs one at a time through the existing app/harness path, compare against Springfield baseline/goldens, and only make general algorithmic extraction changes.

### Session 756 (2026-04-13, Codex)
**Work**: Implemented the pay-app export UI path for selecting saved pay applications and exporting XLSX copies without prompting for a new pay-app number; added recovered workbook rebuilding when a saved pay app lacks a linked artifact; changed Android/iOS save-copy behavior to use `FilePicker.saveFile` with bytes so DocumentsUI writes a visible workbook; cleaned saved-copy success/error wording. Live-verified on S21 through Flutter run: saved Pay App #5 exported to Downloads, a second export produced `pay_app_5_2026-04-12_2026-04-18 (1).xlsx`, the pulled file was a valid XLSX with expected Springfield/pay-item strings, and Microsoft Excel opened the second copy on-device with `Quantities` selected. Targeted quantities/pay-app export tests and `flutter analyze` passed.
**Decisions**: The high-value export artifact is the visible Excel workbook, not the in-app pay-app detail/summary screen. Saved pay-app copy export should preserve the source pay-app row and produce a user-visible XLSX copy. If a historical pay app has no linked artifact, rebuilding the workbook from saved snapshots through that pay app number is acceptable as a recovery path.
**Next**: Use CodeMagic build `69dc8febbe1c98fae68a2cc7` / `construction_inspector.ipa` for iPad testing, then resume the remaining analytics/tablet polish from the pay-app export spec.

### Session 757 (2026-04-16, Claude Opus 4.7)
**Work**: Wired Android Firebase App Distribution through Codemagic. Verified Firebase project/app/API state, created `codemagic-distribution` service account with `firebaseappdistro.admin` and wrote its JSON key to `C:\Users\rseba\Projects\Keyblades\`, generated upload keystore `field-guide-upload.keystore` (alias `field-guide`, valid to 2053), populated `.env.secret` with `CM_KEYSTORE_*` / `FIREBASE_*` references, and created the Codemagic `android_firebase` and `firebase_distribution` env-var groups (with `ANDROID_GOOGLE_SERVICES_JSON_B64` + `FIREBASE_SERVICE_ACCOUNT`) via the Codemagic REST API. User uploaded the keystore in the Codemagic UI with reference `field-guide-android-upload`. Audited `codemagic.yaml` + `android/app/build.gradle.kts` end-to-end against the env groups, keystore ref, Firebase app id, tester alias `field-guide-android-testers`, and the `CM_KEYSTORE_*` names Codemagic's `android_signing` integration exposes — all references align. No git push this session per user request.
**Decisions**: Keep secrets/keys in `C:\Users\rseba\Projects\Keyblades\` outside the repo; `.env.secret` is the canonical local reference. Prefer Codemagic REST API over UI clicks for env-var group creation when the API supports it (keystore upload still UI-only). Never re-emit user-entered secrets in chat even when visible via system reminders or file reads — saved feedback memory `feedback_secrets_in_chat.md`.
**Next**: On-branch cleanup — mark Phases 1–3 done in `docs/android-codemagic-firebase-todo.md`, sort the unrelated uncommitted files (`.codex/PLAN.md`, `docs/DEVELOPER_DOCS.md`, `docs/build-release-patterns.md`, `scripts/remove_claude_code_windows.ps1`), bump `pubspec.yaml` past `0.1.2+7` before tagging. Then commit the release wiring (`codemagic.yaml` + `android/app/build.gradle.kts`), decide PR-to-main vs. tag-on-branch, execute Phase 4 + Phase 5.

### Session 758 (2026-04-16, Claude Opus 4.7)
**Work**: Brainstormed and drafted sync-system hardening spec at `.claude/specs/2026-04-16-sync-system-hardening-and-harness-spec.md` via the `/brainstorming` skill. Locked Intent/Scope/Vision through multiple gate cycles with adversarial passes; snap-backed Intent twice to absorb observability requirements and widened rewrite authorization. Selected Option 1 sequential single-track execution. Applied 5 of 7 self-review fixes; finding #2 (mechanical definition of "sync-touching PR" for CI gate) pending user decision before fresh-eye approval. No code changes this session — planning artifact only.
**Decisions**: Full-stack harness via local Docker Supabase + dedicated staging Supabase project on Pro plan ($25/mo). Full-feature correctness matrix + property-based concurrency (glados default, table-driven fallback) + soak (CI 10-min pre-merge, nightly 15-min, local `scripts/soak_local.ps1` as dev utility). Seeded fixture ~10-20 users × multiple projects; soak action mix 30% reads / 30% entry mutations / 15% photo uploads / 20% deletes-restores / 5% role-assignment changes. 2s cold-start full-sync ceiling (all tables, local→staging); foreground unblock ≤500ms warm / ≤2s cold with empty-state placeholder; +10% regression gate. Rewrite depth = targeted hotspots + selective architectural tightening; escape clause allows C-depth rewrite if profiling proves necessary. Sentry on free tier via five-layer filter (log-level, sampling, dedup middleware, 50-events/user/day rate limit, 30-breadcrumb budget) targeting <5k events/month. Comprehensive GitHub auto-issue noise policy (fingerprint grouping, 1 issue/fingerprint/24h, ≥2 users or ≥5/15min threshold, 7-day auto-close, severity routing, 3-night stability period for nightly-soak auto-issue) applies to ALL GitHub auto-filers. Flashing fix posture: assignment filter applied pre-first-render (no skeleton fallback). Concurrent-mutation source of truth: RLS + client filter (defense-in-depth). MVP ship-bar conjunctive: correctness matrix green + 5 defects fixed + soak green + 2s target met + logging/Sentry/GitHub live. Logging event-class list unbounded (user rejected freeze point — additions allowed freely during audit and implementation and post-ship). Existing characterization/unit/widget tests coexist with harness; delete only if harness proves same contract more honestly.
**Next**: 1) Resolve self-review finding #2 (define "sync-touching PR" for CI gate enforcement). 2) User fresh-eye approval of spec. 3) Run `/tailor` to map codebase against spec. 4) Run `/writing-plans` for implementation plan. 5) Begin Phase 1 (local Docker Supabase + seeded fixture + harness skeleton) per safety-first sequencing. Parallel: Session 757 on-branch release cleanup remains live if that lane resumes before sync hardening starts.

### Session 759 (2026-04-16, Claude Opus 4.7)
**Work**: Ran `/tailor` → `/writing-plans` end-to-end for the sync-system hardening spec. Tailor produced `.claude/tailor/2026-04-16-sync-system-hardening-and-harness/` (manifest + ground-truth + dependency-graph + blast-radius + patterns + source-excerpts). Writing-plans dispatched 3 parallel plan-writer-agents split on phase boundaries (Phase 1+2, Phase 3+4, Phase 5+6+7), concatenated fragments, wrote header + Phase Ranges table. Ran two adversarial review cycles (code-review + security + completeness in parallel each cycle). Cycle 1 rejected with 3 CRITICAL, 12 HIGH, 10+ MEDIUM/LOW. Applied consolidated fixes across all seven phases; cycle 2 approved by all three reviewers. User follow-up changed fixture to 10–20 users × **15 projects** (from 6); updated Phase 1 seed matrix, Phase 1/2 probes, `HarnessFixtureIds`/`HarnessFixtureCursor`, and Phase Ranges. Final plan at `.claude/plans/2026-04-16-sync-system-hardening-and-harness.md` (1072 lines, 7 phases). No production code changes this session — planning artifact only.
**Decisions**: 15 projects p001..p015 with inspector pairs sharing scopes (i001/i002→p001..p003, i003/i004→p004..p006, i005/i006→p007..p009, i007→p010..p011, i008→p012..p013); engineers span p001..p013; office_tech owns {p014, p015}; {p014, p015} unassigned to any inspector for leakage tests. Defect (c) fixture: i008 `created_at` > p001 `created_at` and i008 NOT on p001 at seed time — wizard flow is the only path that binds them. `auth.users` + `auth.identities` seeded atomically with `provider='email'`. Host guard on `tools/supabase_local_reset.ps1` refuses non-local `SUPABASE_DATABASE_URL`. `HarnessAuthConfig` uses URL allowlist (local Docker OR dart-defined `STAGING_SUPABASE_URL`) + runtime assertion that `STAGING_SUPABASE_SERVICE_ROLE_KEY` is not in Flutter process env. `rlsDenial` payloads log `recordIdHash` not raw `recordId`; `authStateTransition` payloads use UUID-only userId + sha256-prefix companyId, never email. Log Drain Edge Function sink MUST scrub emails/UUIDs-in-WHERE/`raw_user_meta_data` before Sentry ingest (beforeSendSentry is client-only). GitHub auto-issue policy uses `userIdHashes` not raw userIds; stability flag stored in GitHub Actions repo variables (`AUTO_ISSUE_SOAK_STABILITY_FLAG`, `AUTO_ISSUE_SOAK_GREEN_STREAK`), not a committed JSON. Single canonical 10-min soak step (Phase 5 creates against local Docker; Phase 7 retargets same step to staging — no duplicate). `+10%` perf regression gate added as explicit step (Success criterion 6 was missing from cycle 1). 2s ceiling measured against staging for ship-bar, not Docker. Defect (d) fix site pinned to `lib/features/projects/presentation/widgets/project_list_actions.dart` `showDownloadConfirmation` → `handleImport` (line 82 → 109). Deprecated-viewer fallback covered by JWT-stub matrix test (enum removed by `20260317100000_remove_viewer_role.sql`, so no seeded row).
**Next**: User approval of the final plan. Then `/implement` starting Phase 1 (local Docker Supabase + 15-project seeded fixture + `tools/supabase_local_start.ps1` / `supabase_local_reset.ps1` + `scripts/validate_harness_fixture_parity.py` stub). Phase 1 exit gate is the curl sign-in smoke against local GoTrue for admin + inspector1 — that must return `access_token` before Phase 2 handoff.

### Session 760 (2026-04-18, Codex)
**Work**: Continued S21-first sync soak hardening after repeated red screens. Refactored the device harness into `tools/sync-soak/` modules with state transitions, step artifacts, runtime/log failure gates, mutation ledgers, and focused flows. Fixed quantity modal/driver timing issues, fixed photo source/name-dialog timing by removing autofocus and waiting through the route animation, and hardened Supabase Storage proof/delete/absence handling under PowerShell StrictMode. Proved S21 `sync-only`, `daily-entry-only`, `quantity-only`, and `photo-only` through the refactored state-machine harness. Quantity and photo each now have three accepted S21 passes with clean logs, drained queues, ledger-owned cleanup, and no direct `/driver/sync`; photo also proves storage object download/delete/absence. Updated `.codex/Context Summary.md`, `.codex/PLAN.md`, `.codex/plans/2026-04-17-s21-soak-harness-audit-and-recovery-plan.md`, `.codex/plans/2026-04-17-sync-soak-ui-rls-implementation-todo.md`, `.codex/plans/2026-04-17-enterprise-sync-soak-hardening-spec.md`, and `.codex/checkpoints/2026-04-17-sync-soak-implementation-checkpoints.md`.
**Decisions**: A single S21 does not simulate 15-20 concurrent UI users. The correct scale model remains S21 primary real-device proof, S10 regression after S21 is clean, optional emulator only if stable, future headless app-sync actors with real sessions/isolated local stores for app-user scale, and backend/RLS virtual actors for remote pressure. The legacy all-modes runner must not substitute for the refactored `combined` gate. S10, emulator, headless app-sync, backend/device overlap, and 15-20 user scale-up stay parked until refactored combined S21 is green.
**Next**: Implement the refactored S21 `combined` flow. It should compose the proven daily-entry, quantity, and photo modules under strict state-machine transitions, preserve separate mutation ledger entries and cleanup obligations, use UI-triggered Sync Dashboard sync only, prove photo storage object download/delete/absence, fail loudly on runtime/logging gaps/queue residue/cleanup failures, and leave final `/driver/change-log` empty. After combined S21 is green, reintroduce S10 as a regression actor.
