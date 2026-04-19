# Entire Codebase Hygiene Refactor Todo Spec

Date: 2026-04-19
Branch audited: `gocr-integration`
Index snapshot: `local/Field_Guide_App-37debbe5` (2026-04-19, 2,905 Dart files / 21,034 symbols)
Status: active controlling todo/spec — whole-repo structural hygiene

## Purpose

This is the forward working list for **whole-codebase structural debt** that is
not already owned by an active decomposition spec. It was assembled from a
jcodemunch repo-health pass, two verification agent sweeps, and a file-size +
layer-import audit. Findings are cross-checked against real source; every claim
in the Audit Baseline is backed by a line number or a `grep`-verifiable path.

This spec is the structural-hygiene companion that is explicitly **not** a
replacement for, and must not conflict with, the following controlling specs:

- `.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md` — sync soak +
  device evidence. This spec defers to it for anything `tools/sync-soak/`,
  `integration_test/sync/soak/`, sync acceptance semantics, and sync-engine
  behavior changes.
- `.codex/plans/2026-04-19-sync-soak-driver-decomposition-todo-spec.md` —
  app-side driver layer decomposition (`lib/core/driver/*`, `harness_seed_data`,
  `driver_diagnostics_handler`, `screen_contract_registry`). This spec defers
  to it for anything inside `lib/core/driver/`.
- `.codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md` — the
  predecessor exception file and soak-layer budgets.

If a lane in this spec touches a surface already owned by one of the specs
above, the item must be re-scoped into that spec or gated behind a predecessor
slice shipping first. This spec picks up everything else — auth, router,
logging, database lifecycle, PDF extraction pipeline, models, DI layer, shared
keys, domain purity, and the custom-lint surface needed to keep the layers
from silently rotting again.

Append implementation notes to (create on first slice):
`.codex/checkpoints/2026-04-19-codebase-hygiene-refactor-progress.md`

## Current Direction

The branch direction is consistent: the feature-first architecture is holding
at the module level (0 dependency cycles, 0 declared-layer violations under a
simple domain/data/core rule set), but the repo has accumulated **localized
god-objects and oversized methods** that make scaling the team painful:

- One ChangeNotifier (`AuthProvider`) is the policy engine for every role
  decision in the app (Ca=109 and growing).
- One static class (`Logger`) has Ca=330 — every change cost-scales with the
  whole codebase.
- `core/` knows about `features/*/presentation/` in at least 20 files,
  including `app_router.dart`, every routes file, and
  `driver_diagnostics_handler.dart`. The rule exists in `rules/architecture.md`
  but is not enforced by custom_lint.
- The PDF extraction pipeline registers **73 stages** (`stage_registry.dart`)
  with no shared `Stage` interface — adding a stage requires hand-editing the
  facade and the registry, and stage orchestration is implicit.
- 30+ models hand-roll `copyWith` with cyclomatic complexities up to 49,
  producing ~10 of the repo's top-40 hotspots from pure boilerplate.
- The shared testing-keys surface is 2,962 LOC across three files and keeps
  growing feature-by-feature.

None of these block shipping. All of them block scaling the number of engineers
safely. This spec gates each refactor behind a measurable exit criterion, a
characterization test, and a reviewable slice size.

## External Pattern Policy

Inherit the External Pattern Policy from
`.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`. One addition:

- [ ] Prefer `freezed` + `json_serializable` as the default for new models.
  These packages are Apache 2.0 / BSD and the deletion payoff versus
  hand-rolled `copyWith`/`==`/`hashCode`/`fromMap`/`toMap` is large. This does
  not retroactively apply to models already shipped; it applies to new models
  and to models touched by this spec's migration lanes.
- [ ] Do not introduce a second state-management system. `provider` +
  `ChangeNotifier` remain the only supported state library per `CLAUDE.md`.
  Reshaping a ChangeNotifier into smaller collaborators (`RolePolicy`,
  `AttributionCache`) is fine; swapping it for Riverpod / BLoC / GetX is not.

## Scope

### In scope

- Auth role/permission policy split (`AuthProvider` → `RolePolicy` +
  `AttributionCache` + `ProfileRefreshScheduler`).
- Logger static-god split (transport / lifecycle / category façade).
- DatabaseService lifecycle-vs-repair split and repair-static relocation.
- Layer-boundary custom_lints:
  - `core_must_not_import_feature_presentation`
  - `domain_must_be_pure_dart`
  - `data_must_not_import_presentation`
- Router decomposition — `FeatureRoutes` interface, move route gating out of
  `form_routes.dart` / `pay_app_routes.dart` / `project_routes.dart` /
  `settings_routes.dart`.
- Model `copyWith`/`==`/`hashCode` migration to `freezed` for the top-10
  hotspots.
- Shared testing-keys co-location per feature.
- PDF extraction pipeline — formalize a `Stage` interface + registry-driven
  orchestration. Decompose `RowMerger.merge`, leave the already-factored
  `row_merger_rules.dart` alone.
- Externalize `construction_description_ocr_word_fixes.dart` and any other
  dictionary-in-code files to assets.
- Sync-engine `PushHandler.push` decomposition (reader / router / reporter).
- Domain purity — remove `package:flutter/foundation.dart` imports from
  `lib/features/*/domain/**` or migrate them to `package:meta/meta.dart`.

### Out of scope (owned elsewhere)

- Anything inside `lib/core/driver/` that `screen_contract_registry`,
  `harness_seed_data`, or `driver_diagnostics_handler._handleActorContext`
  already owns in the driver-decomposition spec. **Exception:** `core/router`
  touching `AuthProvider` is in scope here (this spec) because it is a router
  concern, not a driver concern.
- Any change to sync engine semantics, `SyncCoordinator` as entrypoint,
  `change_log` trigger ownership, or `sync_status` policy. We only restructure
  `PushHandler.push` internals; the public surface is unchanged.
- Any change to accepted device-soak evidence, driver endpoint contracts,
  UI-triggered-sync-only acceptance, or `MOCK_AUTH` policy.
- Any change to the forms acceptance lane (MDOT 1126 / 0582B / 1174R) already
  driven by the unified hardening spec.

## Guardrails

Inherit everything from `CLAUDE.md` (`.claude/CLAUDE.md` and user-global
`.claude/CLAUDE.md`) and the unified hardening spec, plus:

- [ ] Do not weaken custom_lint rules, widen allowlists, or add `// ignore:` or
  `// ignore_for_file:` comments to make a hygiene slice pass. The 5
  `project_provider_*` files currently carry `ignore_for_file: unused_element`
  — no more of those. If a split exposes a legitimate unused-private-member
  surface, delete it rather than silencing.
- [ ] `flutter analyze` and `dart run custom_lint` must stay green on every
  slice.
- [ ] Do not introduce Flutter imports into `lib/features/*/domain/**`. Use
  `package:meta/meta.dart` for `@immutable` and pure-Dart `assert`/`bool.fromEnvironment`
  for `kDebugMode` equivalents.
- [ ] Do not amend-commit into existing hardening work. Each hygiene slice is a
  new commit with the body explaining the mechanical nature of the refactor
  and the characterization-test coverage.
- [ ] Every slice that changes a hotspot method must be preceded by a
  characterization-test commit that pins current behavior with real fixtures.
  (This is how the RowMerger refactor ships safely — 9 test files already
  exercise `RowMerger.merge`; a 10th that snapshots output on a known
  extraction fixture must land before any decomposition.)
- [ ] Do not refactor a model's `copyWith` to `freezed` while that model is
  hotspot-churning in another branch. Check the `unified-hardening` and
  `driver-decomposition` checkpoints for churn claims first.
- [ ] Do not delete a `@visibleForTesting` repair static while it still has
  callers in `test/`. Relocate it with its callers atomically.
- [ ] UI-visible surfaces must be verified on an emulator or device per the
  global `CLAUDE.md` rule. Pure refactors with no UI delta may be verified via
  `flutter test` + `integration_test` only, and the slice body must declare
  "no UI delta" so a later reviewer can confirm.

## Audit Baseline

Measured on branch `gocr-integration` at the re-index above. All numbers below
are reproducible via `find lib -name '*.dart' -exec wc -l {} +` and the
jcodemunch tool calls referenced. Verified by two agent sweeps on 2026-04-19.

### Repo-wide signals (jcodemunch `get_repo_health`, 90-day window)

| Metric | Value | Read |
|---|---:|---|
| Dart files | 2,905 | |
| Symbols | 21,034 | |
| Avg cyclomatic complexity | 3.5 | healthy median |
| Dependency cycles | 0 | no circular imports |
| Declared-layer violations (simple rule set) | 0 | feature-first holds at module level |
| Unstable modules (I ≥ 0.8) | 1,496 | high fan-out, typical for Flutter |
| Logger `Ca` | 330 | #1 central symbol repo-wide |
| AuthProvider `Ca` | 109 | #8 most imported file |
| DatabaseService `Ca` | 139 | #5 most imported file |

### Layer-boundary violations (verified with `grep`)

- [ ] **20 files in `lib/core/**` + `lib/shared/**` import from
  `lib/features/*/presentation/**`.** Verified file list:
  - `lib/core/app_widget.dart`
  - `lib/core/bootstrap/app_lifecycle_initializer.dart`
  - `lib/core/bootstrap/startup_gate.dart`
  - `lib/core/di/app_bootstrap.dart`
  - `lib/core/di/app_dependencies.dart`
  - `lib/core/di/app_providers.dart`
  - `lib/core/driver/driver_diagnostics_handler.dart`
  - `lib/core/driver/flows/navigation_flow_definitions.dart`
  - `lib/core/driver/flows/verification_flow_definitions.dart`
  - `lib/core/driver/screen_registry.dart`
  - `lib/core/router/app_redirect.dart`
  - `lib/core/router/app_router.dart`
  - `lib/core/router/routes/auth_routes.dart`
  - `lib/core/router/routes/entry_routes.dart`
  - `lib/core/router/routes/form_routes.dart`
  - `lib/core/router/routes/pay_app_routes.dart`
  - `lib/core/router/routes/project_routes.dart`
  - `lib/core/router/routes/settings_routes.dart`
  - `lib/core/router/routes/sync_routes.dart`
  - `lib/core/router/scaffold_with_nav_bar.dart`
- [ ] **2 files in `lib/features/*/data/**` import from
  `lib/features/*/presentation/**`:**
  - `lib/features/auth/data/services/auth_provider_session_service.dart`
  - `lib/features/forms/data/services/form_seed_service.dart`
- [ ] **8 files in `lib/features/*/domain/**` import from
  `package:flutter/**`:**
  - `lib/features/sync/domain/sync_diagnostics.dart:14` →
    `package:flutter/foundation.dart`
  - `lib/features/sync/domain/sync_status.dart:16` → foundation
  - `lib/features/sync/domain/sync_error.dart:13` → foundation
  - `lib/features/sync/domain/sync_types.dart:1` → foundation
  - `lib/features/sync/domain/sync_event.dart:15` → foundation
  - `lib/features/auth/domain/usecases/check_inactivity_use_case.dart:1` →
    `package:flutter_secure_storage/flutter_secure_storage.dart`
  - `lib/features/auth/domain/usecases/sign_out_use_case.dart` → flutter
  - `lib/features/settings/domain/usecases/submit_support_ticket_use_case.dart` →
    flutter

### God-surface hotspots (non-test, production code)

| Surface | LOC | Methods | Key method (CC / nesting) | Ca | Spec lane |
|---|---:|---:|---|---:|---|
| `lib/core/logging/logger.dart` | 399 | 27 static | — | 330 | P0: Logger split |
| `lib/features/auth/presentation/providers/auth_provider.dart` | 261 | 35 (≥20 getters) | — | 109 | P0: RolePolicy split |
| `lib/core/database/database_service.dart` + 5 upgrade files | 185 + 1,726 | 16 + N | `_onUpgrade` calls 5 upgrade statics | 139 | P0: DB lifecycle split |
| `lib/core/driver/driver_diagnostics_handler.dart` | 611 | 27 | `_handleActorContext` (c42 / n4, 97 LOC) | — | **owned by driver-decomp spec** |
| `lib/core/router/app_router.dart` | — | — | — | 4 (Ce 21) | P0: router gating split |
| `lib/features/sync/engine/push_handler.dart` | 252 | 3 | `push` (c29 / n7, 130 LOC); ctor takes 13 params | — | P1: PushHandler split |

### Top-10 production-code hotspots by `cyclomatic × log(1+churn)` (jcodemunch)

1. `RowMerger.merge` — cyclomatic **88**, nesting 7, churn 9, hotspot 202.63
2. `RowParserDataRowParser.parse` — cyclomatic **99**, nesting 5, hotspot 137.24
3. `DailyEntry.copyWith` — cyclomatic **49**, churn 10, hotspot 117.50 (manual boilerplate)
4. `ItemDeduplicationWorkflow.deduplicate` — cyclomatic **56**, nesting 8, hotspot 100.34
5. `DriverDiagnosticsHandler._handleActorContext` — cyclomatic **42**, hotspot 92.28
6. `Project.copyWith` — cyclomatic **48**, hotspot 86.00
7. `UserProfile.copyWith` — cyclomatic **41**, hotspot 85.26
8. `formRoutes()` (top-level function) — cyclomatic **35**, hotspot 80.59
9. `PipelineConfig.copyWith` — cyclomatic **40**, hotspot 77.84
10. `PushHandler.push` — cyclomatic **29**, nesting 7, churn 10, hotspot 69.54

### File-size hotspots (over 600 LOC, non-test, non-driver, non-soak)

| File | Lines | Notes |
|---|---:|---|
| `lib/shared/testing_keys/testing_keys.dart` | 1,593 | registry facade |
| `lib/features/pdf/services/extraction/stages/row_merger.dart` | 1,551 | `RowMerger.merge` c88 |
| `lib/features/pdf/services/extraction/stages/row_merger_rules.dart` | 1,543 | **already factored** as 8 rule trios; do not break open |
| `lib/features/pdf/services/extraction/stages/post_consistency_rule_applier.dart` | 1,162 | review for rule-chain shape |
| `lib/features/pdf/services/extraction/stages/row_parser_data_row_parser.dart` | 924 | `.parse` c99 |
| `lib/features/pdf/services/extraction/shared/construction_description_ocr_word_fixes.dart` | 911 | dictionary-in-code → asset |
| `lib/features/pdf/services/extraction/stages/post_processing_stage_support.dart` | 902 | **already factored** via typedefs |
| `lib/features/pdf/services/extraction/shared/description_artifact_cleaner.dart` | 786 | review for dictionary content |
| `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart` | 770 | OCR engine wrapper |
| `lib/features/pdf/services/extraction/ocr/gocr_ocr_cache.dart` | 767 | cache layer |
| `lib/features/pdf/services/idr_pdf_template_writer.dart` | 746 | template writer |
| `lib/shared/testing_keys/entries_keys.dart` | 719 | feature-scope keys |
| `lib/core/driver/screen_contract_registry.dart` | 719 | **owned by driver-decomp spec** |
| `lib/features/pdf/services/extraction/stages/row_classification_support.dart` | 717 | review |
| `lib/core/database/database_schema_metadata.dart` | 697 | schema metadata |
| `lib/features/sync/engine/sync_repair_debug_store.dart` | 689 | sync surface |
| `lib/core/database/database_upgrade_foundation.dart` | 674 | upgrade helper |
| `lib/shared/testing_keys/toolbox_keys.dart` | 650 | feature-scope keys |
| `lib/features/sync/engine/integrity_checker.dart` | 630 | sync surface |
| `lib/core/driver/harness_seed_data.dart` | 615 | **owned by driver-decomp spec** |
| `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_facade.dart` | 614 | pipeline orchestrator |
| `lib/core/driver/driver_diagnostics_handler.dart` | 611 | **owned by driver-decomp spec** |

### Extraction pipeline shape (verified from `stage_registry.dart`)

- [ ] **73 registered stages** running in a hard-coded sequential order.
- [ ] No shared `Stage` abstract class, interface, or mixin.
- [ ] `StageDefinition` (`stage_definition.dart`) is a metadata record only —
  `{id, displayName, pipeline, fixtureFilename, requiredInRegression}`; it does
  not carry a reference to the stage's execute method.
- [ ] `stage_names.dart` is imported by 52 files — stages reference each other
  by string ID.
- [ ] `RowMerger.merge` (lines 90–688) is a hybrid rule-driven state machine
  dispatching on `RowType` with an inner `while (j < rows.length)` loop. The 8
  rule evaluators it consumes already live in `row_merger_rules.dart` and share
  the `ContinuationAttachmentEvaluation` interface — the rules file is **not**
  structural debt; `merge()` itself is.
- [ ] No helper duplication across stage files (verified via cross-file grep of
  `static bool _is…`, `_clamp`, `_midpoint` patterns). Any common-helper
  extraction must be justified by concrete coupling.

### Boilerplate copyWith surface (top-10 manual `copyWith` methods)

All are in `lib/features/**/data/models/` or
`lib/features/pdf/services/extraction/models/` and do not change behavior
between inputs — they are mechanical `a ?? b` branching.

| Model | Method | CC | Churn | Byte length of method |
|---|---|---:|---:|---:|
| `DailyEntry` | `copyWith` | 49 | 10 | — |
| `Project` | `copyWith` | 48 | 5 | — |
| `UserProfile` | `copyWith` | 41 | 7 | — |
| `ParsedBidItem` | `copyWith` | 41 | 5 | 1,258 |
| `PipelineConfig` | `copyWith` | 40 | 6 | — |
| `TodoItem` | `copyWith` | 34 | 7 | — |
| `FormResponse` | `copyWith` | — | — | 1,642 |
| `ProjectAssignment` | `copyWith` | — | — | 1,522 |
| `ProcessedItems` | `copyWith` | — | — | 1,184 |
| `StageReport` | `copyWith` | — | — | 1,276 |

### ChangeNotifier inventory

- [ ] **58 `ChangeNotifier` subclasses** under `lib/features/**`. Biggest by
  LOC (non-test): `AuthProvider` (261), `ProjectAnalyticsProvider` (295),
  `AppConfigProvider` (290), `AppLockProvider` (289), `MdotHubController` (284),
  `ConsentProvider` (265), `PhotoProvider` (262), `FormViewerController` (257),
  `EntryEditingController` (232), `PreferencesService` (232). Only the top two
  (`AuthProvider`, `AppConfigProvider`) have god-class shape; the rest are
  in-bounds.

### `// ignore_for_file:` markers (non-l10n, non-upgrade)

- [ ] 5 `project_provider_*` files carry `ignore_for_file: unused_element` —
  smell; suggests the `project_provider` split left dead private members in the
  part files. Investigate and delete.
- [ ] 3 logger transport files carry `ignore_for_file: no_silent_catch`. The
  transports legitimately swallow write errors to avoid breaking logging, but
  the ignores should be narrowed from `_for_file` to per-catch `// ignore:`.
- [ ] All 6 `database_upgrade_*` ignores are legitimate (migrations need raw
  SQL); do not touch.

---

## Lanes

Lanes are sized so each one ships as an independent PR. `P0` lanes unblock the
rest (custom_lint policy must land before boundary refactors, characterization
tests must land before hotspot method splits). Lane order inside a priority
tier can run in parallel.

---

### P0-A — Layer-boundary custom_lints

Locks in the architecture before we refactor. This is the **highest-ROI, lowest-
risk** slice in the spec: zero runtime change, high future protection, and it
reveals the exact list of future follow-up slices.

- [ ] **P0-A.1 — Add `core_must_not_import_feature_presentation` lint**
  - [ ] Add rule under
    `fg_lint_packages/field_guide_lints/lib/architecture/rules/`.
  - [ ] Rule: files matching `lib/core/**/*.dart` or `lib/shared/**/*.dart`
    must not `import 'package:construction_inspector/features/**/presentation/**'`.
  - [ ] Allowlist entry file — maintain a single
    `fg_lint_packages/field_guide_lints/allowlists/core_presentation_imports.yaml`
    with the 20 files currently violating. Each line is a TODO that feeds a
    later lane (P1-A … P1-D).
  - [ ] Unit test under
    `fg_lint_packages/field_guide_lints/test/architecture/` with positive +
    negative fixtures.
  - [ ] Wire into the existing `architecture_rules.dart` export.
  - Exit: `dart run custom_lint` shows **0 new** failures on `main`. Existing
    20 violations are silenced only via the allowlist — any new violation
    triggers the rule.

- [ ] **P0-A.2 — Add `domain_must_be_pure_dart` lint**
  - [ ] Rule: files matching `lib/features/*/domain/**` must not import
    anything from `package:flutter/*`, `package:cloud_*`, `package:firebase_*`,
    `package:sentry*`, or `package:supabase*`.
  - [ ] Allowlist file enumerating the current 8 violators (see Audit
    Baseline) with a deadline column; each entry is a TODO for P2-E
    (domain-purity fixup).
  - [ ] Unit test with positive + negative fixtures.
  - [ ] Particularly validate: `package:flutter/foundation.dart` **does** count
    as a violation. If the team wants `@immutable`, they must migrate to
    `package:meta/meta.dart`.

- [ ] **P0-A.3 — Add `data_must_not_import_presentation` lint**
  - [ ] Rule: files matching `lib/features/*/data/**` must not import
    `lib/features/**/presentation/**`.
  - [ ] Allowlist file listing the 2 current violators
    (`auth_provider_session_service.dart`, `form_seed_service.dart`) with a
    TODO to resolve in P1-E.
  - [ ] Unit test with positive + negative fixtures.

- [ ] **P0-A.4 — CI wire-up**
  - [ ] Confirm the new rules run in the existing `tools/lint-check.ps1` or
    equivalent pre-commit/CI script. If no such script exists, add one under
    `tools/` — do not hide the lint behind an IDE-only surface.
  - [ ] Update `rules/architecture.md` to name each lint by ID so future
    engineers can find the rule.

Exit criteria (lane-level):
- [ ] `dart analyze && dart run custom_lint` green with the three rules
  enforced and three allowlist files in place.
- [ ] Every allowlist entry has a `# TODO(lane-id):` comment pointing to the
  lane that will remove it.

---

### P0-B — Characterization test harness for PDF-pipeline hotspots

Before decomposing `RowMerger.merge` or any other stage with cyclomatic > 40,
we pin the current outputs.

- [ ] **P0-B.1 — Golden-output snapshot for `RowMerger.merge`**
  - [ ] Add `test/features/pdf/extraction/stages/row_merger/row_merger_snapshot_golden_test.dart`.
  - [ ] Use the existing extraction fixtures that 9 `row_merger_*_test.dart`
    files already consume.
  - [ ] For each fixture, serialize the `merge()` result to a canonical JSON
    and compare against a committed `.golden.json` under
    `test/features/pdf/extraction/stages/row_merger/__snapshots__/`.
  - [ ] Guardrail: the golden file is the artifact of record. Any decomposition
    slice that changes even one byte of golden output must justify why in the
    commit body, plus land a matching golden update.

- [ ] **P0-B.2 — Snapshot for `RowParserDataRowParser.parse`**
  - [ ] Mirror P0-B.1 for `row_parser_data_row_parser.dart`.

- [ ] **P0-B.3 — Snapshot for `ItemDeduplicationWorkflow.deduplicate`**
  - [ ] Mirror P0-B.1 for `item_deduplication_workflow.dart`.

- [ ] **P0-B.4 — Snapshot for `ValueNormalizer.normalize`**
  - [ ] Mirror P0-B.1. Note: `normalize` is already a functional chain of
    repairs (verified), so its cyclomatic 42 is less a hotspot and more an
    advance-snapshot; still land the golden before any re-shaping.

Exit criteria:
- [ ] `flutter test test/features/pdf/extraction/stages/` passes.
- [ ] Every P0-B snapshot file is committed with the fixture it was built
  from, so a reviewer can reproduce.

---

### P0-C — Logger god-class split

Highest Ca in the repo (330). Every touch here is expensive; invest in the
split once.

- [ ] **P0-C.1 — Inventory**
  - [ ] Enumerate the 27 static methods on `Logger` and bucket them into:
    - [ ] **Transport** (file sinks, HTTP, rotation):
      `Logger.init`/`close`/`writeReport`/`verifyWritableDirectory`/
      `_log`/`zoneSpec`/`installLifecycleLogger` + the file-local
      `_formatTimestamp*`/`_getBaseDirectory`/`_getDefaultAppLogDir`.
    - [ ] **Category façade** (10 static shortcuts): `sync`, `pdf`, `db`,
      `auth`, `ocr`, `nav`, `ui`, `photo`, `lifecycle`, `bg`, plus `error`,
      `hypothesis`, `log`.
    - [ ] **PII scrub/test seams**: `scrubSensitiveForTest`,
      `isSensitiveKeyForTest`, `scrubString` (confirmed to already delegate to
      `LogPayloadSanitizer`).
  - [ ] Confirm with jcodemunch `get_symbol_complexity` on each method and
    commit the inventory table into the checkpoint file.

- [ ] **P0-C.2 — Extract `LoggerLifecycle`**
  - [ ] New file: `lib/core/logging/logger_lifecycle.dart`.
  - [ ] Moves: `init`, `close`, `installErrorHandlers`, `zoneSpec`,
    `installLifecycleLogger`.
  - [ ] `Logger.init(...)` becomes a thin façade that forwards to
    `LoggerLifecycle.init(...)`. **Call-sites are not touched** in this slice.
  - [ ] Characterization: `test/core/logging/logger_lifecycle_test.dart` with
    real `Directory.systemTemp` fixtures; verify log dir creation, retention
    pruning, and HTTP-transport opt-in via `DEBUG_SERVER`.

- [ ] **P0-C.3 — Extract `LoggerCategoryFacade`**
  - [ ] New file: `lib/core/logging/logger_category_facade.dart`.
  - [ ] Replace 10 identical 1-line static category methods with a single
    `Logger.category(String category, String msg, {Map<String, dynamic>? data})`
    plus an `enum LogCategory` defined in
    `lib/core/logging/log_category.dart`.
  - [ ] Keep the existing `Logger.sync(...)` / `Logger.pdf(...)` etc. as thin
    deprecation shims for one release (`@Deprecated('use Logger.category(…)')`),
    **do not** delete call-sites in this slice.
  - [ ] Characterization: snapshot tests of what is written to each log file
    for a representative payload per category.

- [ ] **P0-C.4 — Flutter-dep trim**
  - [ ] Audit why `logger.dart` imports `package:flutter/widgets.dart`
    (agent-verified). If it is only for `WidgetsBindingObserver` via
    `installLifecycleLogger`, move that into `LoggerLifecycle` so the category
    façade can stay pure Dart.
  - [ ] Re-verify `Ca` on `lib/core/logging/logger.dart` after the split — it
    should drop from 330 to ≈10.

- [ ] **P0-C.5 — Call-site migration (separate PR, optional)**
  - [ ] Once the facade is deprecated, ship a mechanical codemod that
    rewrites `Logger.sync(...)` → `Logger.category(LogCategory.sync, ...)`.
    This is out-of-band and must not land in the same slice as C.2 or C.3.

Exit criteria:
- [ ] `logger.dart` is a < 150 LOC façade importing lifecycle + categories.
- [ ] All existing tests in `test/core/logging/` pass without modification.
- [ ] `flutter analyze` + `dart run custom_lint` green.
- [ ] `get_repo_health` re-run shows Logger's Ca dropped.

---

### P0-D — AuthProvider → RolePolicy + AttributionCache + ProfileRefreshScheduler

The single highest-leverage refactor: `AuthProvider` is 109 imports deep, and
25+ of its 35 methods are pure-Dart policy that do not need `ChangeNotifier`.

- [ ] **P0-D.1 — Extract `RolePolicy`**
  - [ ] New file: `lib/features/auth/domain/policies/role_policy.dart`.
  - [ ] Plain `const` class or immutable value object built from
    `(UserRole?, UserProfileStatus, ProfileFreshness)`.
  - [ ] Move these getters (confirmed list, verified lines in
    `auth_provider.dart`):
    - [ ] `isAdmin` (162), `isApproved` (163), `userRole` (164)
    - [ ] `canManageProjects` (165), `canEditFieldData` (169),
      `canManageProjectFieldData` (173)
    - [ ] `isEngineer` (177), `isOfficeTechnician` (178), `isInspector` (180)
    - [ ] `canCreateProject` (181), `canReviewInspectorWork` (182)
    - [ ] `canEditEntry({required createdByUserId})` (232),
      `canDeleteProject({required createdByUserId})` (241)
  - [ ] `AuthProvider` keeps a `RolePolicy get policy` getter that reconstructs
    the policy on demand from current profile state. Widgets migrate to
    `context.select<AuthProvider, RolePolicy>((a) => a.policy)` **incrementally**
    in a later slice.
  - [ ] Unit-test `RolePolicy` with every combination of role × profile
    freshness × approval state. This is pure Dart — no widget tests required,
    no `provider_test` setup, no `AuthProvider` double. Target: ~50 micro-tests
    in `test/features/auth/domain/policies/role_policy_test.dart`.

- [ ] **P0-D.2 — Extract `AttributionCache`**
  - [ ] New file: `lib/features/auth/data/services/attribution_cache.dart`.
  - [ ] Moves: `cacheAttributionProfile`, `clearAttributionCache`,
    `getDisplayName(userId)` — all already use `UserAttributionUseCase` and do
    not require `AuthProvider` state.
  - [ ] The cache is provider-injected through existing `AuthProvider`
    constructor so call sites that go through `AuthProvider.getDisplayName`
    keep working, but the cache becomes a standalone class testable with
    fakes.
  - [ ] Tests: `test/features/auth/data/services/attribution_cache_test.dart`.

- [ ] **P0-D.3 — Extract `ProfileRefreshScheduler`**
  - [ ] New file:
    `lib/features/auth/domain/schedulers/profile_refresh_scheduler.dart`.
  - [ ] Moves: `profileRemoteConfirmedAt`, `lastProfileRefreshAttemptAt`,
    `isProfileRefreshDue`, `refreshUserProfile`, and the freshness
    thresholds that `hasUsableProfileForFieldWork` and
    `hasFreshProfileForSharedManagement` (lines 197 and 207) currently inline.
  - [ ] Leaves `AuthProvider.refreshUserProfile()` as a `Future<void>` shim
    that delegates.
  - [ ] Tests: `test/features/auth/domain/schedulers/profile_refresh_scheduler_test.dart`
    with `FakeAsync` + fixed clock.

- [ ] **P0-D.4 — Shrink `AuthProvider`**
  - [ ] Post-split, `AuthProvider` should be ≈100 LOC: constructor, Supabase
    subscription wiring, `_notifyStateChanged`, `dispose`, and thin delegators.
  - [ ] Keep `ChangeNotifier` contract unchanged.

- [ ] **P0-D.5 — Provider wiring**
  - [ ] `lib/features/auth/di/auth_providers.dart` registers `RolePolicy` as a
    `ProxyProvider<AuthProvider, RolePolicy>` so existing tree reads still
    resolve.
  - [ ] `lib/features/auth/di/auth_initializer.dart` constructs the new
    `AttributionCache` and `ProfileRefreshScheduler` and injects them into
    `AuthProvider`.

- [ ] **P0-D.6 — Call-site migration gate**
  - [ ] Widget call-sites that currently read `context.watch<AuthProvider>()`
    for a single `can*` getter migrate to
    `context.select<RolePolicy, bool>((p) => p.canEditFieldData)` over time.
    This is **not part of P0-D** — it is a follow-on lane **P2-A**.

Exit criteria:
- [ ] `auth_provider.dart` under 150 LOC.
- [ ] `RolePolicy` has zero Flutter imports (passes new
  `domain_must_be_pure_dart` lint).
- [ ] All existing `AuthProvider` tests pass unchanged.
- [ ] `role_policy_test.dart` covers every role × approval state × freshness
  combination.

---

### P0-E — DatabaseService lifecycle / repair / testing split

`DatabaseService` currently mixes four concerns; two of them are security-
adjacent (RLS-affecting repairs, `@visibleForTesting` statics). Tighten them.

- [ ] **P0-E.1 — Move repair statics out of `DatabaseService`**
  - [ ] New directory: `lib/core/database/repair/`.
  - [ ] Move `repairNullEntryScopedProjectIds`,
    `rebuildSupportTicketsCanonicalSchema`,
    `purgeProjectAssignmentChangeLogResidue` each into their own file with a
    `@visibleForTesting` top-level function.
  - [ ] Update the **three test callers** atomically in the same PR.
  - [ ] Do NOT delete the original statics in this slice — re-export them
    from `database_service.dart` as `@Deprecated` thin shims for one release.

- [ ] **P0-E.2 — Isolate the in-memory test factory**
  - [ ] New file: `lib/core/database/testing/database_service_testing.dart`.
  - [ ] Moves `factory DatabaseService.forTesting`, `_testing()` constructor,
    `static testInstance`, `initInMemory`, `_initInMemoryDatabase`.
  - [ ] This file is `@visibleForTesting` at the file level and is only
    imported from `test/` and `integration_test/`.

- [ ] **P0-E.3 — Keep `DatabaseService` a pure lifecycle surface**
  - [ ] After E.1 and E.2, `database_service.dart` should hold: singleton,
    FFI init, `database` getter, `_initDatabase`, `close`, and `_onUpgrade`
    (which remains a one-liner delegating to the 5 upgrade helpers).
  - [ ] Target: under 120 LOC.

- [ ] **P0-E.4 — Narrow `ignore_for_file`**
  - [ ] The 6 `database_upgrade_*` files legitimately need
    `avoid_raw_database_delete` and `no_change_log_mutation_outside_sync_owners`
    — migrations are one of the only places those rules should be bypassed.
    Keep the ignores but add a `// REASON:` comment explaining the migration
    context for each file.

Exit criteria:
- [ ] `database_service.dart` under 120 LOC.
- [ ] Every repair static has a new home, its callers migrated, and a
  `@Deprecated` shim in `database_service.dart` for one release.
- [ ] Existing `@visibleForTesting` access paths still resolve (no test broken).

---

### P1-A — Router `FeatureRoutes` interface + auth gating extraction

Finally removes the `core/router` → `features/*/presentation/` coupling for
the five route files (`auth_routes`, `entry_routes`, `form_routes`,
`pay_app_routes`, `project_routes`, `settings_routes`, `sync_routes`).

- [ ] **P1-A.1 — Define `FeatureRoutes`**
  - [ ] New file: `lib/core/router/feature_routes.dart`.
  - [ ] `abstract interface class FeatureRoutes { List<RouteBase> build(); }`.
  - [ ] Optional `RouteGuard? guard` wrapper that is pure-Dart and takes a
    `RolePolicy` (from P0-D) instead of reaching into `AuthProvider`.
  - [ ] Depends on P0-A.1 and P0-D being in place.

- [ ] **P1-A.2 — Move `form_routes.dart` under feature ownership**
  - [ ] New file:
    `lib/features/forms/presentation/routes/forms_feature_routes.dart`.
  - [ ] `formRoutes()` (currently 611 LOC, cyclomatic 35) becomes
    `class FormsFeatureRoutes implements FeatureRoutes` with `build()`
    returning the same tree.
  - [ ] Extract the `_mpResultFromJobResult` helper (line 143) into
    `lib/features/forms/presentation/routes/mp_result_deserializer.dart`.
  - [ ] Auth gating on form routes stops reading `AuthProvider` directly —
    passes through `RolePolicy` or `RouteGuard`.
  - [ ] Delete `lib/core/router/routes/form_routes.dart`.
  - [ ] Update `app_router.dart` to register `FormsFeatureRoutes().build()`
    instead of `formRoutes()`.

- [ ] **P1-A.3 — Repeat A.2 for each route file**
  - [ ] `auth_routes.dart` → `features/auth/presentation/routes/auth_feature_routes.dart`
  - [ ] `entry_routes.dart` → `features/entries/presentation/routes/entries_feature_routes.dart`
  - [ ] `pay_app_routes.dart` → `features/pay_applications/presentation/routes/pay_apps_feature_routes.dart`
  - [ ] `project_routes.dart` → `features/projects/presentation/routes/projects_feature_routes.dart`
  - [ ] `settings_routes.dart` → `features/settings/presentation/routes/settings_feature_routes.dart`
  - [ ] `sync_routes.dart` → `features/sync/presentation/routes/sync_feature_routes.dart`
  - [ ] `toolbox_routes.dart` → `features/toolbox/presentation/routes/toolbox_feature_routes.dart`
  - [ ] Each slice is independent and runs in parallel.

- [ ] **P1-A.4 — Drop allowlist entries**
  - [ ] As each route file moves, remove its entry from the
    `core_must_not_import_feature_presentation` allowlist.
  - [ ] `app_router.dart` still holds a small number of imports for shell
    screens (`scaffold_with_nav_bar.dart`, `app_redirect.dart`); these remain
    allowlisted until P1-B handles them.

- [ ] **P1-A.5 — `app_router.dart` becomes a pure aggregator**
  - [ ] Target: under 200 LOC, only orchestrating `FeatureRoutes` instances
    and the shell. Coupling metric after slice: `Ca` unchanged, `Ce` ≤ 8.

Exit criteria:
- [ ] `grep -r "core/router" lib/features` returns only `app_router.dart`
  import of route containers, nothing about `formRoutes()` et al.
- [ ] `formRoutes` and siblings deleted from `core/`.
- [ ] `allowlists/core_presentation_imports.yaml` shrinks by 7 entries.

---

### P1-B — Remove presentation-provider lookups from `app_redirect.dart` + shell

- [ ] **P1-B.1 — `app_redirect.dart`**
  - [ ] Replace `context.read<AuthProvider>()` calls with `RolePolicy`
    reads via the already-registered `ProxyProvider` from P0-D.5.
  - [ ] If any `AuthProvider`-specific mutations are required, wire them
    through a small `RedirectActions` abstraction in `core/router/`.
  - [ ] Update `test/core/router/app_redirect_test.dart` accordingly (it is
    already the 17th-hottest test file).

- [ ] **P1-B.2 — `scaffold_with_nav_bar.dart`**
  - [ ] Same treatment: route visibility gated via `RolePolicy`, not a
    presentation-layer provider.

Exit criteria:
- [ ] `app_redirect.dart` + `scaffold_with_nav_bar.dart` removed from the
  `core_must_not_import_feature_presentation` allowlist.

---

### P1-C — Bootstrap layer cleanup (`lib/core/bootstrap/`, `lib/core/di/`)

- [ ] **P1-C.1 — `app_bootstrap.dart` / `app_dependencies.dart` / `app_providers.dart`**
  - [ ] These files legitimately register `AuthProvider`,
    `ConsentProvider`, etc. into the `MultiProvider` tree — they must import
    from features. Keep them on the allowlist but **permanently**: they are
    the composition root.
  - [ ] Document each composition-root entry in the allowlist with a comment:
    `# composition-root: registers X into MultiProvider`.
  - [ ] Exit: allowlist documents why each permanent entry is permanent.

- [ ] **P1-C.2 — `startup_gate.dart` / `app_lifecycle_initializer.dart`**
  - [ ] Audit whether their `AuthProvider` reads can be replaced by the
    `RolePolicy` / `AttributionCache` split from P0-D.
  - [ ] If yes, replace and drop from allowlist.
  - [ ] If no (they truly need the mutable notifier), keep on allowlist with
    a documenting comment.

---

### P1-D — Driver layer allowlist reconciliation

`lib/core/driver/*` imports from `features/*/presentation/` are owned by the
driver-decomposition spec. This lane is **coordination only**.

- [ ] **P1-D.1 — Cross-reference driver-decomp spec**
  - [ ] For each of `driver_diagnostics_handler.dart`, `screen_registry.dart`,
    `navigation_flow_definitions.dart`, `verification_flow_definitions.dart`:
    confirm the driver spec owns their eventual `core_must_not_import_feature_presentation`
    fix. If yes, add a TODO tag referencing the driver spec lane that will
    remove them from the allowlist.
  - [ ] If the driver spec does NOT plan to remove a particular presentation
    import, escalate it back into this spec as a new P2 slice.

Exit criteria:
- [ ] Every driver-layer allowlist entry has a `# TODO(driver-decomp-spec:XX)`
  tag.
- [ ] No driver file hides behind the allowlist without an owning lane
  somewhere.

---

### P1-E — Data-layer cleanup: `auth_provider_session_service` + `form_seed_service`

- [ ] **P1-E.1 — `auth_provider_session_service.dart`**
  - [ ] Verify the import of `AuthProvider` from data is legitimate (it's a
    service that reacts to `AuthProvider` state changes).
  - [ ] If it is reading `AuthProvider` for side-effect subscriptions, move
    the subscription wiring into `auth_initializer.dart` (DI layer) and let
    the service take a plain `Stream<SessionEvent>` instead. Service is
    layer-pure after this.
  - [ ] If the dependency is intrinsic (e.g., the service needs the
    `ChangeNotifier` contract), rename it out of `data/` into `di/`.

- [ ] **P1-E.2 — `form_seed_service.dart`**
  - [ ] Same treatment.

Exit criteria:
- [ ] `data_must_not_import_presentation` allowlist is empty.

---

### P1-F — `PushHandler.push` decomposition

Owned here (not by the sync-engine hardening spec) because this is **internal
structure**, not public contract. No sync semantics change.

- [ ] **P1-F.1 — Characterization**
  - [ ] Snapshot every output produced by the 8 existing `push_handler_*_test.dart`
    files. `push_handler_contract_test.dart` is already the de facto contract
    test; freeze its recorded outputs as a golden.
  - [ ] Confirm with the unified hardening spec that no sync-soak lane is
    mid-flight on `PushHandler` — if yes, block P1-F until that slice lands.

- [ ] **P1-F.2 — Extract `PushCycleReader`**
  - [ ] New file: `lib/features/sync/engine/push_cycle_reader.dart`.
  - [ ] Takes `ChangeTracker` + `SyncRegistry`; returns an ordered
    `List<PushCycleBatch>` already FK-sorted.
  - [ ] Deletes lines ~127 through ~151 in `push_handler.push`.

- [ ] **P1-F.3 — Extract `PushRecordRouter`**
  - [ ] New file: `lib/features/sync/engine/push_record_router.dart`.
  - [ ] Takes `SupabaseSync`, `ConflictResolver`, `FileSyncHandler`,
    `SyncHintRemoteEmitter`, `companyId`, `userId`; routes one
    `PushCycleBatch` to its destination.
  - [ ] Deletes the per-record switch block in `push_handler.push`
    (~lines 170-215).

- [ ] **P1-F.4 — Extract `PushProgressReporter`**
  - [ ] New file: `lib/features/sync/engine/push_progress_reporter.dart`.
  - [ ] Takes `SyncEventSink?` + `onProgress` callback; handles the
    `PushResult` accumulation.

- [ ] **P1-F.5 — `PushHandler` becomes orchestrator**
  - [ ] Constructor goes from 13 params to 4: `(reader, router, reporter,
    localStore)`.
  - [ ] `push()` becomes ~20 lines that wire them together.
  - [ ] `validateAndStampCompanyId` stays a static on `PushHandler`.

Exit criteria:
- [ ] `push_handler.dart` under 150 LOC.
- [ ] `PushHandler.push` cyclomatic drops from 29 to ≤ 8.
- [ ] All 8 existing push-handler tests pass unchanged.
- [ ] Nothing in `tools/sync-soak/` or `integration_test/sync/` requires
  touching.

---

### P1-G — Formalize the PDF-extraction `Stage` interface

73 stages with no shared contract is the single biggest cliff for this area
of the code. This lane invests in a seam that the next 12 months of OCR work
will ride on.

- [ ] **P1-G.1 — Define `ExtractionStage`**
  - [ ] New file: `lib/features/pdf/services/extraction/pipeline/stage.dart`.
  - [ ] ```dart
    abstract interface class ExtractionStage<I extends StageInput,
        O extends StageOutput> {
      String get stageId;
      StageDefinition get definition;
      Future<StageRunResult<O>> execute({
        required I input,
        required PipelineConfig config,
        required StageTraceSink? tracer,
      });
    }
    ```
  - [ ] Land `StageRunResult<O>` with `{output, report, warnings,
    repairNotes}` — unifies the ad-hoc tuple patterns already used by
    `PostItemStageResult`, `PostMathValidationStageResult`, etc.

- [ ] **P1-G.2 — Extend `StageRegistry` to be executable**
  - [ ] `stage_registry.dart` gains a `Map<String, ExtractionStage>` alongside
    the existing metadata list.
  - [ ] Populate via explicit registration (no reflection, no codegen).

- [ ] **P1-G.3 — Migrate `extraction_pipeline_facade.dart` (614 LOC)**
  - [ ] Replace hard-coded stage calls with a loop over the registry.
  - [ ] Retain the explicit stage-ordering list as data (not code).
  - [ ] Exit: facade shrinks below 300 LOC and adding a stage requires only
    (a) implementing the interface and (b) appending to the registry file.

- [ ] **P1-G.4 — Do NOT migrate all 73 stages at once**
  - [ ] First 5 stages migrated (any 5 — pick smallest by LOC) as proof the
    interface works. Land as one slice.
  - [ ] Remaining stages migrate opportunistically — each time a stage is
    touched for another reason. Tag the rest with a new lint
    `stage_must_implement_extraction_stage` that is OFF by default and
    allowlist-driven.
  - [ ] Exit: facade no longer contains any direct stage-class references
    after the registry migration, even if the registry itself imports all
    of them.

---

### P1-H — `RowMerger.merge` decomposition

Gated on P0-B.1 (golden snapshot).

- [ ] **P1-H.1 — Extract case handlers**
  - [ ] `RowMerger._mergeDataRow` (lines 151-454, ~243 LOC) into its own
    method — likely as a private method on a new `RowMergerDataRowHandler`
    collaborator that `RowMerger` delegates to.
  - [ ] `RowMerger._mergeContinuationRow` (lines 460-532, ~72 LOC).
  - [ ] `RowMerger._mergeBoilerplateRow` (lines 534-586, ~52 LOC).
  - [ ] Each extract-slice runs the P0-B.1 golden test; zero-byte diff is
    the exit criterion.

- [ ] **P1-H.2 — Rule-chain the 8 evaluators**
  - [ ] The 8 rule evaluators in `row_merger_rules.dart` already share
    `ContinuationAttachmentEvaluation`. Introduce a small
    `RuleChain<Features, Evaluation>` that accumulates evaluator results
    instead of the current inlined 8 `.add(evaluator.evaluate(...))` calls
    inside `merge`.
  - [ ] This is a readability win, not a behavior change. Golden diff must
    remain zero bytes.

- [ ] **P1-H.3 — Reduce nested `while (j < rows.length)` depth**
  - [ ] The `while` at lines 294-445 accumulates trailing price/description
    continuations. Extract into a `TrailingContinuationAccumulator` helper.
  - [ ] Caps max nesting at 4.

Exit criteria:
- [ ] `RowMerger.merge` cyclomatic drops from 88 to ≤ 15.
- [ ] P0-B.1 golden test green with zero-byte diff.
- [ ] All 9 existing `row_merger_*_test.dart` files pass unchanged.

---

### P1-I — Model `copyWith` migration to `freezed` (top 10)

Mechanical refactor, low risk, removes ~10 repo-wide hotspots.

- [ ] **P1-I.1 — Add `freezed` + `freezed_annotation` + `build_runner`**
  - [ ] Add to `dev_dependencies`. Target version current stable.
  - [ ] Add `build.yaml` config scoping `freezed_generator` to
    `lib/features/*/data/models/**` and
    `lib/features/pdf/services/extraction/models/**` only.

- [ ] **P1-I.2 — Migrate models (one per slice)**
  - [ ] Order by hotspot score (highest first):
    - [ ] `DailyEntry` (CC 49, churn 10)
    - [ ] `Project` (CC 48)
    - [ ] `UserProfile` (CC 41)
    - [ ] `ParsedBidItem` (CC 41)
    - [ ] `PipelineConfig` (CC 40)
    - [ ] `TodoItem` (CC 34)
    - [ ] `ProcessedItems`
    - [ ] `FormResponse`
    - [ ] `ProjectAssignment`
    - [ ] `StageReport`
  - [ ] Each slice:
    - [ ] Rewrites the model as `@freezed class X with _$X`.
    - [ ] Regenerates `.freezed.dart` + `.g.dart`.
    - [ ] Asserts `==`/`hashCode`/`toJson`/`fromJson` behavior against the
      pre-migration fixtures (characterization test landed in the same PR).
    - [ ] Deletes the hand-rolled `copyWith`, `==`, `hashCode`, `toMap`,
      `fromMap`.
  - [ ] Runs `dart analyze` + `dart run custom_lint` after each.

- [ ] **P1-I.3 — Block the rest**
  - [ ] After the top 10 migrate, the median model `copyWith` should be CC
    ≤ 20. If not, extend this lane.

Exit criteria:
- [ ] Top-10 models are `freezed`-generated.
- [ ] None of those models appear in the top-40 repo-wide hotspot list.

---

### P2-A — Widget migration to `RolePolicy`

Follow-on to P0-D; purely cosmetic for the call-sites.

- [ ] **P2-A.1 — Mechanical `context.watch<AuthProvider>().canX` →
  `context.select<RolePolicy, bool>((p) => p.canX)` across all widgets.
- [ ] **P2-A.2 — Drop the `ProxyProvider<AuthProvider, RolePolicy>`** shim
  once every call-site migrates; make `RolePolicy` its own top-level
  `ChangeNotifier` fed from `AuthProvider`.
- [ ] **P2-A.3 — Measure rebuild pressure** on the project list screen (which
  currently re-renders on every `AuthProvider.notifyListeners()`). Document
  the frame-time improvement in the checkpoint.

---

### P2-B — Externalize dictionary-in-code files

- [ ] **P2-B.1 — `construction_description_ocr_word_fixes.dart` (911 LOC)**
  - [ ] Verify contents via agent sweep if not already done — the file was
    referenced in the first pass but the 2nd agent noted uncertainty about
    its shape.
  - [ ] If it is a mapping/dictionary, move to
    `assets/ocr/construction_description_word_fixes.json`.
  - [ ] Load at `TesseractEngineV2` / OCR pipeline init.
  - [ ] Keep a thin Dart file that exposes the loaded map behind the same
    API as today.

- [ ] **P2-B.2 — `description_artifact_cleaner.dart` (786 LOC)**
  - [ ] Same audit — if it is rule/dictionary data, extract to JSON.

- [ ] **P2-B.3 — `row_semantic_classification_rules.dart` (544 LOC)**
  - [ ] Same audit.

---

### P2-C — Shared testing-keys co-location

- [ ] **P2-C.1 — Move each key group into its feature**
  - [ ] Current layout (2,962 LOC):
    - `lib/shared/testing_keys/testing_keys.dart` (1,593) — facade + misc
    - `lib/shared/testing_keys/entries_keys.dart` (719)
    - `lib/shared/testing_keys/toolbox_keys.dart` (650)
  - [ ] Target layout: each feature owns its keys under
    `lib/features/<feature>/testing/<feature>_keys.dart` and re-exports into
    `lib/shared/testing_keys.dart` as a thin barrel for tests that currently
    import the facade.
  - [ ] Do NOT break the existing `TestingKeys.` fully-qualified references in
    105 callers — keep a temporary compatibility re-export file.

- [ ] **P2-C.2 — Custom-lint: `testing_keys_must_be_feature_scoped`**
  - [ ] New lint that rejects adding a key to `lib/shared/testing_keys/*`
    that references a feature. Force new keys to live under the feature they
    belong to.

---

### P2-D — ProjectProvider `ignore_for_file: unused_element` cleanup

5 `project_provider_*.dart` files suppress this lint — smell of a prior split
that left dead private members.

- [ ] **P2-D.1 — Audit each file**
  - [ ] `project_provider.dart`
  - [ ] `project_provider_auth_init.dart`
  - [ ] `project_provider_data_actions.dart`
  - [ ] `project_provider_filters.dart`
  - [ ] `project_provider_mutations.dart`
  - [ ] `project_provider_selection.dart`
- [ ] **P2-D.2 — Remove the ignore**
  - [ ] Delete genuinely unused private members.
  - [ ] Make truly cross-file members `package`-visible (no `_` prefix) —
    Dart does not have `package` visibility, so move them into a shared
    `project_provider_internals.dart` private to the feature.
  - [ ] Each file drops its `// ignore_for_file:` comment.

---

### P2-E — Domain purity fixup

Drops the 8 `lib/features/*/domain/` files off the
`domain_must_be_pure_dart` allowlist.

- [ ] **P2-E.1 — `sync/domain/*` (5 files)**
  - [ ] Swap `package:flutter/foundation.dart` for `package:meta/meta.dart`
    in each; `@immutable` is the only reason those files import foundation.
  - [ ] Verify no `kDebugMode` or `ValueNotifier` usage slipped in — if yes,
    move those to the data layer.

- [ ] **P2-E.2 — `auth/domain/usecases/check_inactivity_use_case.dart`**
  - [ ] Imports `flutter_secure_storage` directly. Replace with an injected
    `SecureStorageGateway` interface in `data/`; the usecase takes the
    interface.
  - [ ] Test update: mock the gateway instead of the Flutter plugin.

- [ ] **P2-E.3 — `auth/domain/usecases/sign_out_use_case.dart` +
  `settings/domain/usecases/submit_support_ticket_use_case.dart`**
  - [ ] Same treatment.

Exit criteria:
- [ ] `domain_must_be_pure_dart` allowlist is empty.
- [ ] `lib/features/*/domain/` imports only `dart:*` and
  `package:meta/meta.dart`.

---

### P2-F — Logger category call-site codemod

Follow-on to P0-C; mechanical.

- [ ] **P2-F.1 — Ship a codemod** in `tools/codemods/rewrite_logger_categories.dart`
  that rewrites `Logger.sync(...)` → `Logger.category(LogCategory.sync, ...)`
  etc. across 330 call-sites.
- [ ] **P2-F.2 — Remove the `@Deprecated` shims** from `logger.dart`.
- [ ] Exit: `Logger`'s API surface is one method, not 14.

---

### P3 — Long-tail

- [ ] **P3-A — `form_viewer_controller.dart` (257 LOC)** — audit whether it is
  a god-controller the way `mdot_hub_controller.dart` (284 LOC) is. If yes,
  split.
- [ ] **P3-B — `preferences_service.dart` (232 LOC)** — 195 importers; candidate
  for the same split we are about to do to `AuthProvider`. Defer until P0-D
  ships; revisit if the team feels friction.
- [ ] **P3-C — `integrity_checker.dart` (630 LOC) + `sync_repair_debug_store.dart`
  (689 LOC)** — owned by `unified-hardening` spec; escalate any structural
  debt back there rather than editing here.
- [ ] **P3-D — Per-feature `lib/features/*/presentation/routes/*.dart`
  test coverage** — once P1-A ships, add feature-local route tests replacing
  the repo-wide `test/core/router/app_router_test.dart`.

---

## Evidence requirements (per slice)

Every slice that ships must land with:

- [ ] A checkpoint entry in
  `.codex/checkpoints/2026-04-19-codebase-hygiene-refactor-progress.md`
  including:
  - [ ] Before / after cyclomatic complexity (from jcodemunch
    `get_symbol_complexity`) for each symbol touched.
  - [ ] Before / after file LOC.
  - [ ] Before / after allowlist size for any lint whose allowlist was
    touched.
- [ ] `flutter analyze && dart run custom_lint` green.
- [ ] Tests: the narrowest test file that exercises the touched symbol plus
  any characterization goldens.
- [ ] Where UI is visible: emulator or device verification per `CLAUDE.md`.
  Pure-Dart refactors with **no UI surface** may declare "no UI delta" in the
  commit body.

## Sequencing

```
P0-A (lints)  ──┬── P0-C (Logger split)         ──┐
                │                                  │
                ├── P0-D (RolePolicy)     ──┬── P1-A (routes)  ── P1-B (shell)
                │                            │                   └── P2-A (widgets)
                │                            └── P1-C (bootstrap)
                │
                └── P0-E (DatabaseService)

P0-B (PDF goldens)  ── P1-G (Stage interface)  ── P1-H (RowMerger split)
                                                  └── P2-B (dictionaries)

P1-I (freezed top-10)  ── P2-D (project_provider ignores)

P1-F (PushHandler)  — requires coordination with unified-hardening spec.
                       No cross-dependency with the rest of this list.

P2-E (domain purity)  — requires P0-A.2. Otherwise independent.
P2-C (testing keys)   — independent.
P2-F (logger codemod) — follow-on to P0-C.
```

Parallelism: everything at the same depth can ship in parallel with no merge
conflict as long as each slice touches a disjoint file set. Enforce that by
reading the checkpoint before you pick the next lane.

## Non-goals

- Riverpod / BLoC / GetX migration.
- `sqflite` → `drift` / `floor` migration. The schema-migration path is too
  risky for a hygiene PR; separately owned.
- Replacing `sqflite` FFI init.
- Replacing `go_router` with another routing library.
- Rewriting OCR engines (`tesseract_engine_v2`, `gocr_ocr_cache`).
- Rewriting the forms PDF writer (`idr_pdf_template_writer.dart`, 746 LOC).
- Touching anything under `third_party/`.
- Touching anything under `integration_test/sync/soak/`.
- Touching anything under `tools/sync-soak/`.
- Changing accepted device-evidence semantics.

## Open questions

- [ ] Do we want `freezed` across **all** models (~100+) long-term, or only the
  top-40 by hotspot? The spec stops at top-10 by design; a broader sweep needs
  its own spec.
- [ ] Is `StageRegistry` expected to be runtime-extensible (plugins) or
  compile-time-fixed (explicit registration)? P1-G assumes compile-time-fixed;
  revisit if someone wants a plugin surface.
- [ ] Does the `flutter_secure_storage` → `SecureStorageGateway` shim
  (P2-E.2) need an encrypted-at-rest fallback for tests? Defer to slice.

## Cross-links

- Unified hardening: `.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`
- Driver decomposition: `.codex/plans/2026-04-19-sync-soak-driver-decomposition-todo-spec.md`
- Sync-soak decomposition (predecessor): `.codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`
- Architecture rules (text): `rules/architecture.md`
- Lint package root: `fg_lint_packages/field_guide_lints/`
