Date: 2026-04-08
Branch: `sync-engine-refactor`
Status key: `[ ]` pending, `[-]` in progress, `[x]` done, `[!]` blocked, `[>]` reference

# Beta Central Tracker

This is the canonical append-only beta tracker.

Use this file as the single running source of truth for:
- phases
- sub-phases
- sprint slices
- concrete steps
- blocker status
- verification status
- references to supporting artifacts

Older beta docs remain as supporting artifacts only:
- [2026-04-07-beta-release-unified-todo.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/completed/2026-04-07-beta-release-unified-todo.md)
- [2026-04-08-beta-release-session-handoff.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/completed/2026-04-08-beta-release-session-handoff.md)
- [2026-04-08-beta-research-inventory.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-research-inventory.md)
- [2026-04-08-codemunch-beta-audit-reference.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-codemunch-beta-audit-reference.md)

Primary external audit source for this tracker:
- Notion export snapshot: `C:\Users\rseba\AppData\Local\Temp\notion_beta_export_632c1bec\inner\Field_Guide_App_Notion_Import_2026-04-07 33cc3411c1b58029a802cc3289f9cbab.md`

## Finish Criteria

Beta is not done until all of these are true:
- `flutter analyze` is clean.
- `dart run custom_lint` is clean.
- shipped forms export is proven correct against live template mappings.
- pay-app export flow is proven from UI trigger through artifact persistence and detail flows.
- routing is standardized and production route contracts are covered.
- provider/controller architecture drift is burned down behind explicit endpoints.
- the current pre-merge security and migration blockers from the Notion audit are either closed or formally descoped.
- remaining oversized core files are either decomposed or explicitly moved out of beta scope.

## Current Source Of Truth

[>] Notion blocker snapshot
- `driver_server.dart` remains a pre-production god-object blocker.
- `codex-admin-sql` edge function remains an undocumented security review blocker.
- `debug_emit_sync_hint_self` remains a pre-prod gate/remove item.
- sync-hint migration squash and rollback coverage remain open.
- i18n/responsive/a11y remain real gaps, but they are below the current export/routing/security hard blockers.

[>] Code-backed status snapshot
- forms export proof is closed for shipped beta forms: IDR, MDOT 0582B, MDOT 1126.
- routing audit found no missing production named routes.
- driver/harness shell/forms routing drift has been fixed.
- auth/gallery/photos/projects provider drift wave is largely integrated and targeted tests are green.
- sync-hint RPC ownership and post-RPC refresh lint issues are closed.
- `dart run custom_lint` is clean.
- current repo-backed size and importance inventory is captured in the research artifact.

## Phase 1: Release-Critical Proof And Routing

### 1.1 Forms Export Fidelity

[x] Prove shipped forms export against live template fields
- IDR
- MDOT 0582B
- MDOT 1126

[x] Re-verify pay-app regression slices after shared export changes

### 1.2 Routing Standardization

[x] Standardize production `go_router` callers on named routes
[x] Add lint coverage for raw path navigation drift
[x] Repair auth redirect proof with a testable force-reauth seam
[x] Align driver/harness shell routing with production `ShellRoute`
[x] Align driver/harness forms routing with `FormGalleryScreen` and `/form/:responseId`
[x] Add real driver route contract coverage

### 1.3 Routing Gaps Audit

[x] Audit production route definitions for missing named routes
Outcome:
- no glaring missing production routes were found in the live router
- the main gap was driver/harness drift, not production route absence

## Phase 2: Architecture Standardization

### 2.1 Provider/Controller Endpoint Drift

[x] Close earlier drift in calculator / todos / support / consent / admin / contractors / locations / quantities / entries / pay-app
[x] Continue auth / gallery / photos / projects drift cleanup
Current status:
- integrated enough to keep targeted auth/photos/projects tests green
- final custom-lint cleanup still in progress this session

### 2.2 Routing And Endpoint Standardization Rules

[x] Keep `prefer_named_go_router_navigation`
[x] Add `driver_route_contract_sync`
[ ] Consider a follow-up lint for route registration consistency if new drift appears after the current cleanup

### 2.3 Oversized Surface Audit

[-] Keep one current inventory of god-sized files and central symbols
Reference:
- [2026-04-08-beta-research-inventory.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-research-inventory.md)

## Phase 3: Pre-Merge Security And Migration Blockers

### 3.1 Security Surfaces From Notion Audit

[ ] Audit `supabase/functions/codex-admin-sql`
[ ] Gate or delete `debug_emit_sync_hint_self`
[ ] Decide whether `daily-sync-push` rate limiting is beta-blocking or post-beta hardening

### 3.2 Migration Safety

[ ] Squash the sync-hint migration churn into a clean final-state migration set before merge
[ ] Backfill rollback SQL for the recent uncovered migration wave
[ ] Decide whether rollback CI enforcement lands in beta or immediately after beta

## Phase 4: Oversized Core Surface Reduction

### 4.1 Highest Priority Files

[ ] `lib/core/driver/driver_server.dart`
[ ] `lib/core/database/database_service.dart`
[ ] `lib/features/forms/data/services/form_pdf_service.dart`
[ ] `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`

### 4.2 Next Queue

[ ] `lib/services/soft_delete_service.dart`
[ ] `lib/features/pdf/services/pdf_service.dart`
[ ] `lib/features/projects/data/services/project_lifecycle_service.dart`
[ ] `lib/features/sync/application/realtime_hint_handler.dart`

## Phase 5: Platform And Product Gaps

These remain visible in the Notion audit, but they are below the current export/routing/security blockers unless elevated by new evidence.

[ ] i18n scaffolding decision
[ ] responsive shell/layout adoption
[ ] accessibility audit on high-traffic screens
[ ] settings data export UI scope decision
[ ] biometric/PIN lock
[ ] GDPR/account deletion
[ ] weather offline cache
[ ] contractor bulk import

## Active Sprint Slice: 2026-04-08 Routing + Tracker Consolidation

### Slice A: Centralize the beta planning surface

[x] create one canonical beta tracker
[x] create one durable CodeMunch + Notion research artifact
[x] wire both artifacts into the existing beta docs

### Slice B: Finish current lint drift

[-] eliminate remaining `custom_lint` warnings without weakening rules
Open at slice start:
- sync-hint RPC owner warning
- driver diagnostics post-RPC refresh warning
- max-import-count warnings in 3 tests

### Slice C: Cross-reference Notion blockers with current repo reality

[x] forms-export blocker is now closed in code, even though Notion snapshot still listed forms test gaps
[x] routing production gap concern was checked; the real issue was driver parity, now closed
[ ] security/migration blockers still need code follow-through
[ ] oversized core files remain open and must stay on the queue

## Verification Ledger

Most recently confirmed green before this tracker was created:
- `flutter analyze`
- routing suite around `app_router`, `app_redirect`, `scaffold_with_nav_bar`, driver route contract, and form dispatcher
- forms export mapping matrix and shipped PDF filler tests
- targeted auth/photos/projects/provider tests

Current session still needs re-run after the last lint-cleanup patch lands:
- `flutter analyze`

Current session already re-verified:
- `dart run custom_lint`

## Append Log

### 2026-04-08 09:xx ET

- Collapsed the beta planning sprawl into this central tracker.
- Bound the tracker to the live Notion export snapshot instead of only the prior local mirror.
- Added a dedicated research inventory artifact for CodeMunch-backed size/ownership findings.
- Kept older beta handoff/todo docs as supporting references instead of deleting history mid-push.
- Cleaned the remaining `custom_lint` backlog to zero.
- Moved the real Codex tree under `.claude/codex` and replaced the root `.codex` path with a junction so the app repo keeps ignoring `.codex` while the nested `.claude` repo can track the actual Codex files.
