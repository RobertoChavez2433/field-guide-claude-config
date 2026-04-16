# UI E2E Feature Harness Refactor

**Work Type:** Refactor+ (test harness + production UI)
**Date:** 2026-04-16
**Spec Author:** Paired conversation (Opus 4.7 + user)

---

## Intent

**Problem:** The existing 121-flow e2e harness is a linear dependency chain that is slow, forward-only, and does not exercise backward traversal, deep-link entry, nav-bar switch mid-flow, or tablet layouts. The production UI has accumulated navigation bugs and the tablet experience is broken in places.

**Who feels it:**
- You, as the developer trying to trust a build
- Downstream inspector users hitting nav/nesting bugs
- Tablet users whose form factor has little test coverage today

**Success criteria (all three must hold):**
1. **Coverage** — every in-scope feature has scenario-DAG + forward + backward + deep-link coverage × admin / engineer / officeTechnician / inspector × S21 phone and S10 tablet, in the expanded harness.
2. **Regression baseline** — the new harness establishes a stable baseline; bugs found during audit and migration are fixed and locked behind coverage. No pre-existing burn-down list — the audit produces it as it goes.
3. **Structural** — every `_screen.dart` file has been reviewed in a blanket sweep against the testability bar (below); every feature is expressible as a scenario-DAG node.

**Why now:** Combined driver — tablet UI closeout is active and untested, nav bugs have accumulated beyond what manual catches, and the chain-based harness is the structural blocker to closing both gaps.

---

## Scope

### In scope (v1)

- Audit of the current 121-flow harness producing the **feature taxonomy** and **testability bar rubric** (both below as deliverables)
- Redesign of the test harness around a **scenario-DAG seed model**; preconditions resolved by direct repository seeding (or new `/driver/seed` endpoint) instead of replaying setup UI
- **Blanket screen sweep** — all ~55 `_screen.dart` files audited and refactored to the testability bar; no pre-decided exclusions
- **Per-feature coverage checklist** — see Sub-flow Catalog below
- **Matrix** — admin × engineer × officeTechnician × inspector × S21 × S10, auto-expanded per sub-flow with collapse rules
- **Sync UI screens** (`/sync/dashboard`, `/sync/conflicts`, sync status icons, settings sync button) included for UX/nav coverage
- **Manual M-flows and pay-app P-flows** — UX/UI-facing ones absorbed into new harness; pure-sync ones stay untouched
- **Per-feature cutover** — as each feature migrates, its old chain-based flows retire; back-and-forth churn during migration is acceptable
- **Migration runs in parallel, not ordered** — all features migrate at once
- **New PDF AcroForm inspection helper** — research first, build if nothing fits; byte-compare fallback where AcroForm inspection isn't feasible
- **Registries kept in sync** — `screen_registry`, `screen_contract_registry`, `flow_registry` updated atomically with feature specs

### Deferred (not v1, not forever)

- Nav-graph property walks (glados + go_router graph + sentinel-key invariants)
- Windows desktop coverage
- iOS automated coverage (stays best-effort from user reports)
- Offline resilience / stress testing
- Nightly device-lab CI job (comes after a stable baseline exists)

### Out of scope

- Sync engine flows S01-S21 — stay on existing dual-device harness unchanged
- New auth modes, RLS changes, role additions
- Parallel testing framework (Patrol, Maestro, Detox, Appium)
- Riverpod or second state-management system

### Constraints

- `flutter analyze`, `dart run custom_lint`, `scripts/audit_ui_file_sizes.ps1`, `scripts/validate_sync_adapter_registry.py` stay green
- No ignore comments, analyzer excludes, or severity downgrades
- No test-only methods or lifecycle hooks on production classes
- Feature-first split preserved; `provider` + `ChangeNotifier` only
- `go_router` remains the routing primitive
- `SyncCoordinator` / `SyncErrorClassifier` / `SyncStatus` stay owned
- Soft-delete default, `change_log` trigger-owned
- 300-line presentation file ceiling preserved
- No Flutter imports in `domain/`

### Non-goals

- No parallel testing framework
- No Patrol / Maestro / Detox / Appium
- No nav-graph property walks in this spec
- No lint weakening
- No production test-only hooks
- No sync engine / auth / RLS / schema changes
- No Riverpod
- No iOS, Windows, or offline resilience coverage in this spec

---

## Vision

**User journey:**
1. Developer or agent runs `/test <feature> [sub-flow] [--device s10|s21]`
2. Harness reads `.claude/test-flows/features/<feature>.md` (prose + fenced YAML)
3. Scenario-DAG resolver seeds SQLite for declared preconditions
4. Harness runs the selected sub-flows across matrix cells that survive collapse rules
5. Per-sub-flow checkpoint + per-feature report written under `.claude/test-results/`
6. Pass/fail surfaces with concrete cell + missing-key or export-failure reason

**Key interactions:**
- Select scope at invocation — whole feature, single sub-flow, or matrix-narrowed slice
- Scenario-DAG seeding replaces UI replay for preconditions
- Sub-flows run independently; agents can pick edge cases without the whole e2e
- Failure produces actionable output — sub-flow name, matrix cell, specific key or export assertion that failed

**Acceptance-by-feel:**
- Feature-scoped run finishes fast (no replaying setup UI)
- Adding a new feature means writing one `.md` + YAML, updating the three registries, and getting coverage on day one
- Failure output tells you exactly which sub-flow × role × device × assertion broke

---

## Selected Shape (Refactor+ tail)

### Pain Point

Existing harness is a chain. Features are not expressible in isolation. Forward-only happy-path coverage misses nav-nesting bugs. Tablet layouts are untested. Production UI has drifted below the testability bar in places (hardcoded colors/keys, oversized presentation files).

### Target Shape

Feature → named sub-flows, each scenario-DAG-seeded and matrix-expanded, authored in markdown + fenced YAML, runnable in isolation via the existing HTTP driver.

### Ambition Level

**Option:** Whole subsystem (test harness + blanket production UI sweep)

**Why this over the others:** User chose full migration for all features in one spec with per-feature cutover and blanket sweep. Minimum or single-file ambition would not address the chain, nav-edge, or tablet pain simultaneously. Phased splitting was rejected — execution happens in parallel, not ordered.

**Phase scope:** This spec covers Phase 1 of 2. Phase 2 (nav-graph property walks, nightly device-lab CI, iOS automation, offline stress) is explicitly deferred to a future spec once the Phase 1 baseline is stable.

### Blast Radius Budget

- **Files touched:**
  - `.claude/skills/test/` — modify existing skill
  - `.claude/test-flows/features/*.md` — new per-feature files (replaces `tiers/*.md`)
  - `.claude/test-flows/tiers/*.md` — deleted after cutover; content recycled into features
  - `.claude/test-flows/sync/*.md` — untouched
  - `.claude/test-flows/flow-dependencies.md` — rewritten as feature taxonomy index
  - `lib/shared/testing_keys/*.dart` — additions as new sentinel keys are introduced
  - `lib/core/driver/screen_registry.dart` / `screen_contract_registry.dart` / `flow_registry.dart` — per-feature updates
  - `lib/core/driver/driver_*.dart` — new `/driver/seed` endpoint
  - `lib/features/**/presentation/screens/*.dart` — blanket sweep against rubric
  - `lib/features/**/presentation/widgets/*.dart` — token + key remediation
  - `tools/start-driver.ps1` / `stop-driver.ps1` — updated if seed endpoint requires it
  - New: PDF AcroForm inspection helper (location TBD in `/tailor`)

- **Behavior changes allowed:**
  - Presentation file decomposition — allowed
  - `Colors.*` → `Theme.of(context).colorScheme.*` / `FieldGuideColors.*` — allowed
  - Hardcoded `Key('...')` → `TestingKeys.*` — allowed
  - Screen split into composables — allowed, must preserve user-visible behavior
  - New sentinel `TestingKeys` exposed — allowed
  - Route guards / redirects — only where existing behavior is wrong; confirmed bug fixes logged

- **Rollback strategy:** Single PR on the current `gocr-integration` branch. All feature migrations and screen remediations land together. No feature flags — test infra is low-risk at runtime. Within the PR, per-feature cutover still applies as a commit cadence (each feature's old flows retire in the same commit as its new `.md` and remediated screens), but delivery is one merge.

### Test Coverage Floor

- Before a feature's old flows retire, its new feature-spec `.md` must run green on both S21 and S10 for all in-matrix sub-flows.
- Driver registries updated in the same commit as the feature spec.
- No feature may cut over with `fixme:` or `skip:` in its sub-flow YAML unless approved.

---

## Audit Deliverables (baked in)

### Feature Taxonomy

UX-facing features for per-feature `.md` migration (16):

| # | Feature | Primary screens | Role gating |
|---|---------|-----------------|-------------|
| 1 | `auth` | login, register, forgot-password, otp-verification, update-password, update-required, profile-setup, company-setup, pending-approval, account-status | all |
| 2 | `dashboard` | project-dashboard, home | all |
| 3 | `projects` | project-list, project-setup (tabs: details, locations, contractors, bid-items, assignments) | admin / engineer / officeTechnician create/edit; inspector read-only (per `UserRole.canManageProjects`) |
| 4 | `entries` | entries-list, drafts-list, entry-editor, entry-review, review-summary, entry-pdf-preview | all (per `UserRole.canEditFieldData`) |
| 5 | `forms` | mdot-hub, form-new-dispatcher, mdot-1126-form, mdot-1174r-form, form-fill, form-viewer, form-gallery, form-pdf-preview, proctor-entry, quick-test-entry, weights-entry | all |
| 6 | `pay_applications` | pay-application-detail, contractor-comparison | admin / engineer / officeTechnician (project-management surface) |
| 7 | `quantities` | quantities, quantity-calculator | all |
| 8 | `analytics` | project-analytics | admin / engineer / officeTechnician |
| 9 | `pdf` | pdf-import-preview, mp-import-preview | admin / engineer / officeTechnician (project-management surface) |
| 10 | `gallery` | gallery | all |
| 11 | `toolbox` | toolbox-home | all |
| 12 | `calculator` | calculator (HMA + concrete tabs) | all |
| 13 | `todos` | todos | all |
| 14 | `settings` | settings, edit-profile, saved-exports, legal-document, oss-licenses, personnel-types, app-lock-settings, app-lock-unlock, trash, consent, help-support, admin-dashboard | admin-only subset (admin-dashboard, personnel-types, trash); rest all |
| 15 | `sync_ui` | sync-dashboard, conflict-viewer | all |
| 16 | `contractors` | contractor-selection | all |

Role gating source of truth: `lib/features/auth/data/models/user_role.dart` (`UserRole.canManageProjects`, `UserRole.canEditFieldData`, `UserRole.isAdmin`). Sub-flow YAML `appliesTo.roles` must match the role gating column above; any mismatch is a rubric failure.

Infrastructure-only modules (no per-feature `.md`, but screens/widgets still audited for testability bar): `pdf` extraction services, `photos`, `locations`, `signatures`, `weather`.

### Testability Bar Rubric

Every `_screen.dart` must pass all 11:

1. **Design tokens** — no raw `Colors.*` in presentation (15 files currently fail)
2. **Testing keys** — no hardcoded `Key('...')` in presentation (8 files currently fail); every interactive widget references `TestingKeys.*`
3. **Sentinel key** — screen exposes one unique `TestingKeys.*` sentinel for `/driver/find` identification
4. **File-size compliance** — `scripts/audit_ui_file_sizes.ps1` green (300-line ceiling)
5. **Decomposition** — screens >200 lines split into composable widgets; mixins/helpers use existing `*_mixin.dart` / `*_helpers.dart` / `*_actions.dart` pattern
6. **Wiring integrity** — provider/controller composition lives in `di/*screen_providers.dart`; no ad-hoc wiring
7. **go_router compliance** — route in `lib/core/router/routes/*.dart`; no raw `Navigator.push`
8. **Back behavior** — pop returns to the previous `go_router` stack entry; if the stack is empty at the feature's entry screen, redirects to the feature's declared entry route rather than stranding the back stack
9. **Responsive** — renders on 360dp (S21) and ~800dp (S10) without overflow or hidden controls
10. **Mounted guard** — every async-gap `context` use is preceded by a `mounted` check
11. **Driver contract** — if sync-visible, present in `screen_registry` + `screen_contract_registry` + `flow_registry`

*Rubric items 3–5, 7, 10, 11 are rule-sourced (from `.claude/rules/frontend/flutter-ui.md`, `.claude/rules/testing/testing.md`, and the 300-line ceiling enforced by `scripts/audit_ui_file_sizes.ps1`), not invented for this spec. Items 1, 2, 6, 8, 9 derive from explicit user confirmations during brainstorming.*

### Sub-flow Catalog (per-feature checklist)

Every feature's `.md` declares sub-flows from this fixed catalog. Sub-flows not applicable to a feature are omitted (collapse rule: missing = N/A, not failure).

| Sub-flow name | Purpose |
|---------------|---------|
| `forward_happy` | End-to-end forward happy path through the feature |
| `backward_traversal` | Walk back from terminal screen to feature entry using back button and nav bar |
| `nav_bar_switch_mid_flow` | Switch tabs mid-edit; assert state preservation or discard prompt |
| `back_at_root` | Press back at feature entry screen; assert exit / home / redirect |
| `deep_link_entry` | Cold-start via `/driver/navigate` into a nested route; assert load or guard redirect |
| `tab_switch_mid_edit` | Switch bottom-nav during unsaved edit; assert discard behavior |
| `orientation_change` | Rotate device mid-flow; assert no data loss or crash |
| `form_completeness` | Fill every field of a form completely; verify PDF preview populates every cell; verify export PDF is a non-flattened editable AcroForm |
| `export_verification` | Trigger export; verify OS file creation; verify content sentinel or AcroForm integrity |
| `role_restriction` | Assert role-gated routes behave correctly per `UserRole` permissions: inspector denied project-management surfaces, admin-only surfaces denied to non-admin roles, engineer and officeTechnician allowed where `canManageProjects` applies. Covers the ground T85-T91 currently test. |

### Matrix Collapse Rules

Declared in YAML `appliesTo:` block per sub-flow:

```yaml
appliesTo:
  roles: [admin, engineer, officeTechnician, inspector]   # drop any to collapse
  devices: [s21, s10]                                     # drop any to collapse
```

Common collapses:
- Admin-only surfaces (admin-dashboard, personnel-types, trash): `roles: [admin]`
- Project-management surfaces (pay_applications, analytics, pdf import): `roles: [admin, engineer, officeTechnician]`
- Field-data-only features with inspector read-only expectations: split into two sub-flows — `forward_happy` (`roles: [admin, engineer, officeTechnician]`) plus `role_restriction` (`roles: [inspector]` proving denial)
- Orientation sub-flow: one role per device is sufficient; do not multiply by role unless layout differs by role

### Per-Feature `.md` Template

Every feature file follows this shape:

````markdown
# Feature: <name>

## Purpose
<one paragraph — what the feature does, why it has its own file>

## Screens
- <screen_name>: <file path>
- ...

## Preconditions catalog
<each named precondition used by sub-flows below>

## Sub-flows

```yaml
- name: forward_happy
  requires: [project_draft, location_a]
  appliesTo:
    roles: [admin, inspector]
    devices: [s21, s10]
  steps:
    - tap: <TestingKey>
    - text: { key: <TestingKey>, value: "..." }
    - wait: <TestingKey>
  assertions:
    - find: <sentinel_key>
    - currentRoute: <expected path>
```

## Retired flow IDs
<list of T##, P##, M## IDs this feature replaces; paste from audit>
````

### Old-Tier → New-Feature Mapping (audit output)

| Old tier / flow range | New feature file | Notes |
|-----------------------|------------------|-------|
| T01-T04 (auth) | `auth.md` | direct map |
| T05-T14 (project setup) | `projects.md` | T14 (search) stays under projects |
| T15-T30 (entry crud + lifecycle) | `entries.md` | combines tiers 2 + 3 |
| T31-T34 (todos) | `todos.md` | |
| T35-T37, T43, T74 (forms) | `forms.md` | split: mdot-hub vs per-form sub-flows |
| T38-T39 (calculator) | `calculator.md` | |
| T40 (gallery) | `gallery.md` | |
| T41-T42 (pdf/export) | absorbed into owning feature's `export_verification` sub-flow | |
| T44-T52 (settings/profile) | `settings.md` | |
| T53-T58 (admin ops) | `settings.md` (admin section) + `projects.md` (archive) | |
| T59-T67 (edit mutations) | distributed by feature | |
| T68-T77 (delete ops) | distributed by feature | |
| T85-T91 (role/permission) | `role_restriction` sub-flows across features | |
| T92-T96 (nav/dashboard) | absorbed as `nav_bar_switch_mid_flow` / `deep_link_entry` sub-flows | |
| P01-P05 (pay app) | `pay_applications.md` | |
| P06 (pay app sync) | stays on sync harness | out of scope |
| M01-M13 manual | UX ones absorbed per feature; sync-only ones untouched | |
| S01-S21 sync | untouched on existing dual-device harness | out of scope |

### PDF AcroForm Inspection Helper

Research first. Dart/Flutter candidates to evaluate in `/tailor`:
- `pdf` package (nfet/dart_pdf) — write-only, not useful
- `syncfusion_flutter_pdf` — reads AcroForm fields; commercial license concern
- `pdfrx` — newer reader; check AcroForm field enumeration
- Byte-compare fallback — canonical golden PDF per form type

Helper must expose **the following capabilities** (exact API surface is a sketch to be locked in `/tailor`, not a contract):
- Read every AcroForm field with name + value + editability flag
- Assert that every expected field has a non-empty value (population check)
- Assert that the PDF still has an AcroForm dictionary and fields are editable (flatten check)

Exact implementation decision and final API shape deferred to `/tailor`.

---

## Open Questions / Deferred to Tailor

1. `/driver/seed` endpoint shape — direct repository call vs HTTP body with SQL fixtures vs named factory invocation
2. PDF AcroForm helper — which Dart package, license implications, fallback strategy
3. Sentinel-key assignment for screens that currently lack one — one per screen, naming convention
4. Feature-spec YAML schema — exact validation rules and where validator lives
5. Retirement bookkeeping — how old tier files are deleted and what proves coverage parity before retirement
6. Registry update automation — whether any codegen is added, or updates stay manual
7. Migration parallelism — how agents coordinate when multiple features are migrated simultaneously
