# UI E2E Feature Harness Refactor Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Replace the chain-based 121-flow e2e harness with a scenario-DAG seed model authored per feature, while bringing every `_screen.dart` up to the testability bar across S21 phone and S10 tablet.

**Spec:** `.claude/specs/2026-04-16-ui-e2e-feature-harness-refactor-spec.md`
**Tailor:** `.claude/tailor/2026-04-16-ui-e2e-feature-harness-refactor/`

**Architecture:** New `/driver/seed` HTTP endpoint wraps existing top-level `seedBaseData` / `seedScreenData` / `seedPayAppData` functions (declared in `harness_seed_data.dart` and `harness_seed_pay_app_data.dart`) using a precondition-keyed body. A `PdfAcroFormInspector` test helper (located under `test/support/`) built on already-installed `syncfusion_flutter_pdf` powers `form_completeness` / `export_verification` assertions. Sixteen per-feature `.claude/test-flows/features/*.md` files replace `tiers/*.md`, each authored as prose + fenced YAML consumed by `.claude/skills/test/`. Production remediation sweeps rubric items 1/2/4/5 (tokens, keys, 300-line ceiling, decomposition) and a dedicated dynamic-rubric sweep covers items 6-10 (wiring / go_router / back / responsive / mounted) across the 57 `_screen.dart` surface (count verified by `Get-ChildItem -Recurse -Filter '*_screen.dart' lib/features | Measure-Object` at execution time — spec quoted ~55, tailor verified 57).

**Tech Stack:** Flutter + Dart (`provider` + `ChangeNotifier`), `go_router`, SQLite via `DatabaseService`, `syncfusion_flutter_pdf`, `dart:io` HttpServer for driver, PowerShell audit scripts, Python validator scripts.

**Blast Radius:** Single PR on `gocr-integration`. `.claude/test-flows/` (7 tier files deleted, 16 feature files created, index rewritten), `.claude/skills/test/SKILL.md` updated, `lib/core/driver/` (seed endpoint + shared HTTP guards extraction + 2 registries + harness seed switch), `lib/shared/testing_keys/` (sentinel additions in existing + new per-feature files, facade re-exports), `lib/features/**/presentation/` (166 color occurrences, 10 hardcoded-Key offenders, 45 file-size violations, 1 `ValueKey` go_router-key violation at `project_routes.dart`), `test/support/pdf_acroform_inspector.dart` (new test-scope helper), `tools/validate_feature_spec.py` (new), `tools/validate_retired_flow_ids.py` (new), `test/core/driver/registry_alignment_test.dart` (new).

## Phase Ranges

| Phase | Name | Start | End |
| --- | --- | --- | --- |
| 1 | Foundation & Tooling | 30 | 257 |
| 2 | Testing Keys + Color Tokens Sweep | 260 | 328 |
| 3 | Presentation Decomposition (300-line ceiling) | 331 | 428 |
| 4 | Rubric Items 6-10 Dynamic Sweep | 432 | 471 |
| 5 | Sentinel Keys + Screen Contract Expansion | 474 | 557 |
| 6 | Feature Spec Authoring | 560 | 633 |
| 7 | Old Tier Retirement & Final Gate | 636 | 712 |

---

## Phase 1: Foundation & Tooling

Build the shared infrastructure every feature cutover depends on: the `/driver/seed` HTTP endpoint with extracted shared guards, the PDF AcroForm inspector, the feature-spec validator, the retired-flow-ID auditor, the registry-alignment guard test, and the test-flow docs rewrite.

### Shell convention for every verification step in this plan

Use Windows PowerShell (or `pwsh`) for all Flutter/Dart commands, per `rules/platform-standards.md`. Do not run these commands from Git Bash. Example invocations used throughout the plan:

- `flutter analyze`
- `dart run custom_lint`
- `pwsh -File scripts/audit_ui_file_sizes.ps1`
- `python scripts/validate_sync_adapter_registry.py`
- `flutter test <path>` (only for tests the plan creates — existing suites stay untouched unless called out)

If a dedicated repo wrapper is added in the future, swap the bare command for the wrapper at that time; none currently exists for `analyze` / `custom_lint` / `test`.

### Step 1.1 — Extract shared driver-HTTP guards

**Decision (closes security-review finding on gate drift):** `_rejectReleaseOrProfile` and `_readJsonBody` are copy-pasted today inside `driver_data_sync_handler.dart:169-177` and `:179-199`. Extract them to a shared file so the new seed handler (and any future driver handler) cannot drift on security gates.

**Files to create:**

- `lib/core/driver/driver_http_guards.dart`:
  - Top-level `Future<bool> rejectReleaseOrProfile(HttpResponse response)` — lifted verbatim from `driver_data_sync_handler.dart:169-177`.
  - Top-level `Future<Map<String, dynamic>?> readJsonBody(HttpRequest request, {int? maxBytes})` — lifted verbatim from `driver_data_sync_handler.dart:179-199`.
  - Re-use the existing `_sendJson` logger pattern via a small helper in the same file (`sendJson(HttpResponse, int, Map<String, dynamic>)`).

**Files to modify:**

- `lib/core/driver/driver_data_sync_handler.dart`:
  - Remove the in-class `_rejectReleaseOrProfile` / `_readJsonBody` definitions.
  - Import from `driver_http_guards.dart` and update call sites.

**Verify:**

```
flutter analyze
dart run custom_lint
flutter test test/core/driver/
```

### Step 1.2 — Add `/driver/seed` endpoint (precondition-keyed body, args-schema validated)

**Decision (resolves spec open question #1):** body is precondition-keyed, matching feature-spec YAML `requires:`. Shape:

```json
POST /driver/seed
{
  "preconditions": [
    {"name": "base_data"},
    {"name": "pay_app_draft", "args": {"payAppId": "…"}}
  ]
}
```

**Files to create:**

- `lib/core/driver/driver_seed_handler.dart`:
  - `class DriverSeedRoutes { static const seed = '/driver/seed'; static bool matches(String path) => path == seed; }`
  - `class DriverSeedHandler { DriverSeedHandler({required DatabaseService? databaseService}); final DatabaseService? _databaseService; … }`.
  - `Future<bool> handle(HttpRequest req, HttpResponse res)`:
    - `if (!DriverSeedRoutes.matches(req.uri.path)) return false;`
    - Reject non-POST with 405 `{'error': 'Method not allowed'}` and return `true`.
    - `if (await rejectReleaseOrProfile(res)) return true;` (imported from `driver_http_guards.dart`).
    - If `_databaseService == null`, 503 `{'error': 'Database not ready'}`.
    - `final body = await readJsonBody(req, maxBytes: 64 * 1024);` — `null` → 400 `{'error': 'Invalid JSON'}`.
    - Iterate `body['preconditions']` (must be `List`) and dispatch each `{name: String, args: Map<String, dynamic>}` through `_dispatchPrecondition`.
    - Return 200 `{'seeded': [<names>]}` on success.
  - `Future<void> _dispatchPrecondition(String name, Map<String, dynamic> args)`:
    - `base_data` → `seedBaseData(db)` (top-level function in `harness_seed_data.dart`). No args allowed.
    - `project_draft`, `location_a`, `contractor_a`, `entry_draft`, `entry_submitted`, `form_response_draft`, `pay_app_draft`, `pdf_import_result_staged`, `pending_profile`, `otp_required_profile`, `rejected_profile` → dispatch to named seeder branches in `harness_seed_data.dart` (added in Step 1.3). Each precondition declares its **expected args keyset** as a `const Set<String>` constant in the same file; unknown/extra keys return 400 `{'error': 'Unknown arg for <name>: <key>'}` before invoking the seeder.
    - Unknown precondition name → 400 `{'error': 'Unknown precondition: <name>'}`.

- `test/core/driver/driver_seed_handler_test.dart`:
  - POST with `base_data` only → 200, seeds baseline.
  - POST with `{"preconditions": [{"name": "pay_app_draft", "args": {"payAppId": "X"}}]}` → 200.
  - POST with unknown precondition name → 400.
  - POST with known precondition + extra arg key → 400 with `Unknown arg for <name>: <key>`.
  - GET `/driver/seed` → `handle` returns `true` with 405.
  - Other path → `handle` returns `false`.
  - Release-mode simulation (set via test override of `kReleaseMode` flag fixture) → 403. If `kReleaseMode` cannot be mocked at test time, assert the branch via a unit test of `rejectReleaseOrProfile` in `driver_http_guards_test.dart` instead.

**Files to modify:**

- `lib/core/driver/driver_server.dart`:
  - Inject `DriverSeedHandler _seedHandler` via the constructor alongside `_dataSyncHandler`.
  - In `_handleRequest` (body at `driver_server.dart:141-174`), insert `if (await _seedHandler.handle(request, res)) return;` **immediately after** the `_dataSyncHandler` line at `:165-167` and **before** `_shellHandler.handle` at `:168-170`. Rationale: seed is data-layer concern and belongs next to `_dataSyncHandler` in the cascade; running it before `_shellHandler` ensures `/driver/find` lookups that race against a seed command serialize correctly.

### Step 1.3 — Extend `harness_seed_data.dart` with named precondition seeders

**Files to modify:**

- `lib/core/driver/harness_seed_data.dart`:
  - Add a top-level `Future<void> seedPrecondition(DatabaseService db, String name, Map<String, dynamic> args)` switch that maps:
    - `project_draft` → insert an unsubmitted project (status `draft`) using `ProjectLocalDatasource.upsert(...)` with id from `args['projectId'] ?? HarnessSeedDefaults.defaultProjectId`. Follow the existing `_clearBaseSeedRows` + insert idempotency pattern.
    - `location_a` → upsert a default location using `LocationLocalDatasource`.
    - `contractor_a` → upsert a default contractor using `ContractorLocalDatasource`.
    - `entry_draft` → upsert a draft `DailyEntry` (status `draft`).
    - `entry_submitted` → upsert a submitted `DailyEntry` (status `submitted`).
    - `form_response_draft` → upsert a draft `FormResponse` via `FormResponseLocalDatasource`.
    - `pay_app_draft` → delegate to `seedPayAppData(db, args)` (already top-level in `harness_seed_pay_app_data.dart`).
    - `pdf_import_result_staged` → stage a `PdfImportResult` row (or its persistence equivalent) so `/import/preview/:projectId` receives a non-null `state.extra` via a new route-extra registry shim added in this step — or, if the router uses `state.extra` exclusively without a registry, the precondition seeds the underlying `bid_items` row set and the sub-flow deep-links to the post-import consumer screen instead. Writer picks the exact shape based on a 15-minute read of `lib/features/pdf/presentation/` import flow at execution time; plan locks the invariant: after this precondition runs, `deep_link_entry` to `/import/preview/:projectId` either succeeds or the sub-flow is explicitly collapsed to N/A in `pdf.md` with a note.
    - `pending_profile`, `otp_required_profile`, `rejected_profile` → upsert a `UserProfile` via `UserProfileLocalDatasource` with the membership-status / auth-state flags set to the appropriate non-approved state. Each profile uses a distinct id (`HarnessSeedDefaults.pendingUserId`, etc. — add constants in `harness_seed_defaults.dart`). Closes security-review finding: baseline `seedBaseData` inserts an approved admin, which would short-circuit approval gates — auth sub-flows testing those gates MUST use these preconditions instead.
  - Preserve the existing `seedScreenData` and `_seedFormData` paths unchanged; `seedPrecondition` is purely additive.
  - Extend the per-precondition args keyset constants: `const _projectDraftArgs = <String>{'projectId'};` etc., exported for `DriverSeedHandler` use.

### Step 1.4 — Build `PdfAcroFormInspector` in test scope

**Files to create:**

- `test/support/pdf_acroform_inspector.dart` (test-scope; resolves security-review finding against production import graph pollution):
  ```dart
  class PdfAcroFormInspector {
    PdfAcroFormInspector(Uint8List pdfBytes) : _doc = PdfDocument(inputBytes: pdfBytes);
    final PdfDocument _doc;

    bool get hasEditableAcroForm;              // _doc.form != null && _doc.form.fields.count > 0
    Map<String, String?> readAllFieldValues(); // iterate form.fields[i], downcast per subtype
    List<String> findUnpopulatedFields(List<String> expectedNames);
    void dispose();
  }
  ```
  - Enumerate `form.fields[i]` and downcast per type: `PdfLoadedTextBoxField.text`, `PdfLoadedCheckBoxField.isChecked` (stringified), `PdfLoadedComboBoxField.selectedValue`, `PdfLoadedListBoxField.selectedValues.join(',')`, `PdfLoadedRadioButtonListField.selectedValue`.
  - Public-API only; do not declare `ignore_for_file: implementation_imports` (the existing exception in `form_pdf_field_writer.dart` is for *writing* read-only fields; inspection is read-only and public).
  - Always `try/finally` on `.dispose()` — mirror `form_pdf_rendering_service.dart:24-53` lifecycle.
- `test/support/pdf_acroform_inspector_test.dart`:
  - Round-trip a known AcroForm template (reuse the fixture already used in `test/features/forms/services/form_pdf_field_writer_test.dart`).
  - Assert `hasEditableAcroForm`, `readAllFieldValues` key/value exactness, `findUnpopulatedFields` gap reporting.
  - Flattened-form case: produce a flattened fixture in a `setUpAll` step (run the form writer with `document.form.flattenAllFields()` then save), reopen via the inspector, assert `hasEditableAcroForm == false`.

**Constraint:** `test/support/` keeps the helper off the production import graph. `form_completeness` / `export_verification` sub-flows reach the helper via the test runner, not via `lib/`. No `pubspec.yaml` changes (`syncfusion_flutter_pdf: ^32.1.25` already present).

### Step 1.5 — Create `tools/validate_feature_spec.py`

**Files to create:**

- `tools/validate_feature_spec.py` — follows `scripts/validate_sync_adapter_registry.py` CLI shape (exit 0 clean, 1 findings; JSON-per-line summary + human tail). Checks:
  - Every sub-flow `name` is in the catalog: `forward_happy, backward_traversal, nav_bar_switch_mid_flow, back_at_root, deep_link_entry, tab_switch_mid_edit, orientation_change, form_completeness, export_verification, role_restriction`.
  - `appliesTo.roles` is a subset of `[admin, engineer, officeTechnician, inspector]` **and** aligns with the feature's role-gating column in spec § Feature Taxonomy. For features with a non-`all` role-gating row (projects, entries, pay_applications, analytics, pdf, settings/admin), the validator REQUIRES a `role_restriction` sub-flow asserting the denied role(s). Closes security-review finding on role mis-gating.
  - `appliesTo.devices` is a subset of `[s21, s10]`.
  - `requires` entries exist in the feature's `## Preconditions catalog` section **and** map to a seeder branch — validator greps `harness_seed_data.dart` for `case '<name>':` in `seedPrecondition`, or for a literal `'<name>'` string in the `_dispatchPrecondition` switch of `driver_seed_handler.dart`. Closes completeness-review finding on precondition cross-ref.
  - Every `tap`/`text`/`wait`/`find` step references a `TestingKey` string literal that appears in `lib/shared/testing_keys/*.dart` (regex `Key\('<literal>'\)` match).
  - Every `navigate` / `current_route` literal matches a `go_router` path from `lib/core/router/routes/*.dart` (pattern match — `:paramId` placeholders are OK).
  - Auth sub-flows: `base_data` precondition is FORBIDDEN when the sub-flow's `steps` reach `/verify-otp`, `/pending-approval`, or `/account-status` — the validator flags this and requires a distinct profile precondition (`pending_profile` / `otp_required_profile` / `rejected_profile`).

**CLI:**

```
python tools/validate_feature_spec.py --all
python tools/validate_feature_spec.py --feature auth
```

### Step 1.6 — Create `tools/validate_retired_flow_ids.py`

**Files to create:**

- `tools/validate_retired_flow_ids.py` (closes completeness-review finding on unnamed audit script):
  - Reads `.claude/test-flows/flow-dependencies.md` (post-rewrite) for the Retired Flow ID Index.
  - Reads each `.claude/test-flows/features/*.md` for its `## Retired flow IDs` block.
  - Asserts every ID in the index (T01-T96, P01-P06, M01-M13) appears in **exactly one** feature's retired-IDs block, or is explicitly marked out-of-scope (S01-S21, P06, any sync-only M-IDs).
  - Exit 0 / 1 pattern.
- CLI invoked in Phase 7 final gate.

### Step 1.7 — Add Dart registry-alignment guard test

**Files to create:**

- `test/core/driver/registry_alignment_test.dart`:
  - `import '...screen_registry.dart'` exposes `screenRegistry` map (top-level in `lib/core/driver/screen_registry.dart`).
  - `import '...screen_contract_registry.dart'` exposes `screenContracts` map.
  - `import '...flow_registry.dart'` exposes `flowRegistry` map.
  - Assertion A: `for (final id in screenContracts.keys) expect(screenRegistry.containsKey(id), isTrue, reason: 'Contract $id missing from screenRegistry');`
  - Assertion B: `for (final f in flowRegistry.values) for (final screenId in f.seedScreens) expect(screenRegistry.containsKey(screenId), isTrue);` — `FlowDefinition.seedScreens` is typed `List<String>` (see `lib/core/driver/flows/flow_definition.dart:16`), so iterate the list directly, not `.keys`.
  - Assertion C: `for (final contract in screenContracts.values) expect(contract.rootKey, isNotNull);` — then follow with a stronger check that the sentinel is traceable to a `TestingKeys.*` symbol by importing `lib/shared/testing_keys/testing_keys.dart` and asserting every contract's `rootKey` appears in a hand-collected `kAllTestingKeys` set defined in the test file. (Closes code-review nit on no-op assertion.)

**Decision (resolves spec open question #3):** every **sync-visible** screen (currently 16 + the new contracts added in Phase 5) requires a `ScreenContract`. Non-sync-visible screens stay rubric-checked (items 1-10) without a contract. `HomeScreen` at `lib/features/entries/presentation/screens/home_screen.dart` stays rubric-only — it is a shell index, not a sync-visible terminal surface; the `dashboard.md` feature file references it but does not own it (ownership stays with the entries feature; see Phase 6 authoring rules). `ProjectDashboardScreen` gains a contract (Phase 5) because `deep_link_entry` sub-flows target it.

### Step 1.8 — Rewrite `.claude/test-flows/flow-dependencies.md` as feature taxonomy index

**Files to modify:**

- `.claude/test-flows/flow-dependencies.md` — full rewrite:
  - Top: `Feature Taxonomy` table from spec § Feature Taxonomy (16 rows).
  - Middle: `Sub-flow Catalog` table (10 sub-flows).
  - Bottom: `Retired Flow ID Index` — flat list of all 121 old IDs with a `→ <feature>.md` target, populated from spec § Old-Tier → New-Feature Mapping **and** the M-ID absorption table below:

**M01-M13 → feature absorption table (locked now, closes code-review finding on deferred mapping):**

| M-ID | Purpose | Target file | Notes |
|---|---|---|---|
| M01 | Register + OTP + profile/company setup | `auth.md` | uses `otp_required_profile` + fresh-state preconditions, not `base_data` |
| M02 | Forgot password + OTP reset | `auth.md` | uses `otp_required_profile` |
| M03 | Import pay items from PDF | `pdf.md` | uses `pdf_import_result_staged` |
| M04 | Import M&P from PDF | `pdf.md` | uses `pdf_import_result_staged` variant |
| M05 | Capture photo (camera) | `entries.md` | camera is entry-attached |
| M07 | Download remote project | `projects.md` | sync-touching but driven through project-list UI, not `/driver/sync` |
| M08 | Deactivate / reactivate member | `settings.md` | admin-dashboard surface |
| M09 | Form section-by-section submit | `forms.md` | 0582B has no global submit — matches `form_completeness` per-section assertions |
| M10 | Approve join request | `settings.md` | admin surface |
| M11 | Reject join request | `settings.md` | admin surface |
| M12 | Quantity calculator from entry | `entries.md` | entry-review entry point |
| M13 | Personnel types from entry | `entries.md` | entry-editor entry point |

Note: M06 is absent from the source `.claude/test-flows/tiers/manual-flows.md` table (the sequence jumps from M05 to M07). If the retired-flow index synthesis ever surfaces an M06, treat it as out-of-scope (likely a pre-removed placeholder) and annotate the index row accordingly. `tools/validate_retired_flow_ids.py` accepts explicit out-of-scope annotations.

Every UX-relevant M-ID lands in exactly one feature; nothing is sync-only, so `.claude/test-flows/tiers/manual-flows.md` deletes in Phase 7 with the rest of the tier cluster. Sync IDs (S01-S21) and P06 marked `→ sync harness (out of scope)`.

### Step 1.9 — Update `.claude/skills/test/SKILL.md`

**Files to modify:**

- `.claude/skills/test/SKILL.md`:
  - Replace the `Required References` block's `tiers/*.md` entries with `features/*.md` (16 entries) plus the existing `references/driver-and-navigation.md` + `references/debug-server-and-logs.md`.
  - Pin the selector grammar in one place: `/test <feature> [sub-flow] [--role admin|engineer|officeTechnician|inspector] [--device s10|s21]`. When `--role` is omitted, the runner iterates over the sub-flow's `appliesTo.roles`. When `--device` is omitted, iterates over `appliesTo.devices`. Closes completeness-review finding on role iteration mechanism.
  - Preserve the Sync Hard Rules verbatim (UI-only sync, dismiss-keyboard after text-entry, etc.).

**Verify for Phase 1:**

```
flutter analyze
dart run custom_lint
pwsh -File scripts/audit_ui_file_sizes.ps1
python scripts/validate_sync_adapter_registry.py
python tools/validate_feature_spec.py --all           # exits 0 on empty features/ set
python tools/validate_retired_flow_ids.py             # exits 0 after flow-dependencies rewrite
flutter test test/core/driver/driver_seed_handler_test.dart test/core/driver/registry_alignment_test.dart test/support/pdf_acroform_inspector_test.dart
```

---

## Phase 2: Testing Keys + Color Tokens Sweep

Feature-agnostic remediation of rubric items 1 (design tokens) and 2 (testing keys). Before any feature file is authored in Phase 6, every interactive widget it will reference must already use `TestingKeys.*`, and every presentation file must be token-clean.

### Step 2.1 — Replace hardcoded `Key('…')` with typed `TestingKeys.*`

**Decision (closes code-review finding on hedged key-owner placement):** the following new per-feature key files are created now, so every future sentinel has a clear home:

- `lib/shared/testing_keys/forms_keys.dart` (new) — exports `FormsTestingKeys`.
- `lib/shared/testing_keys/gallery_keys.dart` (new) — exports `GalleryTestingKeys`. (Gallery is taxonomy feature #10; not a sub-surface of toolbox.)
- `lib/shared/testing_keys/pdf_keys.dart` (new) — exports `PdfTestingKeys`.
- `lib/shared/testing_keys/analytics_keys.dart` (new) — exports `AnalyticsTestingKeys`.

Each new file follows the structure of `sync_keys.dart:1-96` (private `_()` constructor, snake-case `Key('…')` literals, factory keys `static Key foo(String id) => Key('foo_$id')`). Wire the new classes into `testing_keys.dart` facade with `static const fooScreen = FormsTestingKeys.fooScreen;`-style delegations.

**Files to modify (10 occurrences across 5 files — exhaustive from tailor `blast-radius.md`):**

- `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart` (1) — move literal to `SyncTestingKeys`; reference via `TestingKeys`.
- `lib/features/sync/presentation/support/conflict_presentation_mapper.dart` (6) — move to `SyncTestingKeys`; conflict-card factory key becomes `static Key conflictCard(String id) => Key('conflict_card_$id')`.
- `lib/features/forms/presentation/widgets/rainfall_events_editor.dart` (1) — move to `FormsTestingKeys` (new file).
- `lib/features/gallery/presentation/widgets/gallery_filter_sheet.dart` (1) — move to `GalleryTestingKeys` (new file).
- `lib/features/entries/presentation/controllers/entry_activities_controller.dart` (1) — move to `EntriesTestingKeys`.

**Naming convention (from tailor `testing-keys-module.md`):** lowercase snake-case literal; factory keys take an id parameter.

**Verify:**

```
flutter analyze
dart run custom_lint
```

Additional audit scan (must return zero matches after Step 2.1):

```
(Grep pattern `Key\('` under `lib/features/*/presentation/` and `lib/core/design_system/`)
```

### Step 2.2 — Replace `Colors.*` literals with design tokens

**Files to modify (166 occurrences across 107 files — too long to inline; regenerate via Grep `Colors\.` under `lib/features/*/presentation/` and `lib/core/design_system/` at execution time).**

**High-density starting points (from tailor):**

- `lib/features/entries/presentation/screens/review_summary_screen.dart` (11)
- `lib/features/entries/presentation/utils/weather_helpers.dart` (8)
- `lib/features/pdf/presentation/widgets/mp_import_preview_sections.dart` (5)
- `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` (4)
- `lib/features/settings/presentation/widgets/admin_dashboard_widgets.dart` (4)
- `lib/features/entries/presentation/widgets/home_calendar_section.dart` (4)

**Replacement rules (from `rules/frontend/flutter-ui.md`):**

- Brand/semantic colors → `FieldGuideColors.of(context).<role>` (primary, onPrimary, surface, outline, error, etc.).
- Opacities on theme colors → `.withValues(alpha: 0.<n>)` on the token.
- Background literals (`Colors.white`, `Colors.black`) on material surfaces → `Theme.of(context).colorScheme.surface` / `.onSurface`.
- Severity/weather color ladders → add to the existing severity-color token owner (read the design-system module at execution time for the canonical owner — `lib/core/design_system/color_tokens.dart` or sibling). Do not add one-off `Color(0x…)` consts in features.

**Constraint:** no new dependencies, no `// ignore: deprecated_member_use` for `.withOpacity`, no hex-literal fallbacks unless the design system already exposes the exact shade.

**Verify:**

```
flutter analyze
dart run custom_lint
```

After Phase 2.2, repeat the `Colors.` Grep — must return zero matches under `presentation/` and `core/design_system/`. Any residual is a rubric item 1 failure.

---

## Phase 3: Presentation Decomposition (300-line ceiling)

Rubric items 4 and 5. Forty-five files currently fail `scripts/audit_ui_file_sizes.ps1` (full list in tailor `blast-radius.md`). Decompose each using the repo's existing suffix pattern. The full list is authoritative from `pwsh -File scripts/audit_ui_file_sizes.ps1` at execution time — the batches below are scoped by feature surface, not by arbitrary count targets. Any file not listed by name here but flagged by the audit gets decomposed under the same rules.

### Canonical suffixes (verified to exist in repo)

- `_screen.dart` — `StatelessWidget` / `StatefulWidget` + `build` only.
- `_state_mixin.dart` — `State<…>` lifecycle + state fields.
- `_actions.dart` — user-intent → provider calls.
- `_controller.dart` — `ChangeNotifier` + provider plumbing.
- `_helpers.dart` — pure-Dart helpers.
- `_sections.dart` / `_section.dart` / `_card.dart` — presentational widgets.
- `_shell.dart` — wrapping scaffold with slots.
- `_body_content.dart` — inner content widget.

**Rule (closes code-review finding on invented suffixes):** every new file must use one of the eight suffixes above. Never introduce `_slots.dart`, `_builders.dart`, `_body.dart`, `_mix_section.dart`, or other novel suffixes — if none of the canonical suffixes fit, open a discussion before adding a new convention.

### Step 3.1 — Batch Forms + Calculator

| Lines | File | Strategy |
|---:|---|---|
| 680 | `lib/features/calculator/presentation/widgets/hma_calculator_tab.dart` | Hoist mix-design section → `hma_calculator_mix_section.dart` (new widget file using `_section` suffix variant that exists in repo); hoist result rendering → `hma_calculator_result_section.dart`; tab widget stays as shell + provider binding |
| 677 | `lib/features/forms/presentation/screens/mdot_1174r_form_screen.dart` | Mirror 1126 pattern: extract `mdot_1174r_shell.dart` + split existing `mdot_1174r_sections.dart` further |
| 577 | `lib/features/forms/presentation/screens/mdot_1174r_sections.dart` | Split into per-step section files under same folder |
| 545 | `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart` | Extract `mdot_1126_actions.dart` (`_actions` suffix mirror of `form_pdf_action_owner.dart`); hoist shell to `mdot_1126_shell.dart` |
| 525 | `lib/features/forms/presentation/screens/form_gallery_screen.dart` | Hoist sections into existing `form_gallery_sections.dart` (confirm existence; if missing, create) |
| 512 | `lib/features/forms/presentation/screens/mdot_1126_steps.dart` | Split per step into `mdot_1126_step_<n>_section.dart` |
| 490 | `lib/features/calculator/presentation/widgets/concrete_calculator_tab.dart` | Mirror `hma_calculator_tab.dart` strategy |
| 427 | `lib/features/forms/presentation/widgets/hub_quick_test_content.dart` | Split to `hub_quick_test_body_content.dart` + `hub_quick_test_actions.dart` |
| 387 | `lib/features/forms/presentation/widgets/form_workflow_shell.dart` | Hoist slot widgets into individual `*_section.dart` files; shell stays thin |
| 377 | `lib/features/forms/presentation/support/form_pdf_action_owner.dart` | Hoist PDF-branch helpers to `form_pdf_action_owner_helpers.dart` (`_helpers` suffix) |
| 357 | `lib/features/forms/presentation/widgets/form_repeated_row_composer.dart` | Hoist row-builders to `form_repeated_row_composer_helpers.dart` |
| 335 | `lib/features/forms/presentation/widgets/form_viewer_sections.dart` | Extract dense sections |
| 321 | `lib/features/forms/presentation/screens/form_viewer_screen.dart` | Reduce build() by relying on existing `form_viewer_sections.dart` |
| 311 | `lib/features/forms/presentation/widgets/hub_compact_accordion_sections.dart` | Split by accordion category |
| 311 | `lib/features/calculator/presentation/widgets/concrete_shape_input_cards.dart` | Split per shape (rectangle / cylinder / trapezoid) into own `_card.dart` files |

### Step 3.2 — Batch Entries

| Lines | File | Strategy |
|---:|---|---|
| 565 | `lib/features/entries/presentation/screens/entry_review_screen.dart` | Hoist review rendering → `entry_review_sections.dart` |
| 380 | `lib/features/entries/presentation/controllers/pdf_data_builder.dart` | Split per PDF block via private helpers in `pdf_data_builder_helpers.dart` |
| 377 | `lib/features/entries/presentation/screens/entry_editor_state_mixin.dart` | Hoist validation / draft branches to dedicated mixins (`entry_editor_validation_mixin.dart`, `entry_editor_draft_mixin.dart`) — all use the `_state_mixin` canonical suffix variant |
| 372 | `lib/features/entries/presentation/screens/drafts_list_screen.dart` | Hoist list rendering → `drafts_list_sections.dart` |
| 356 | `lib/features/entries/presentation/screens/review_summary_screen.dart` | Hoist sections → `review_summary_sections.dart`; Phase 2.2 removes 11 color literals already |
| 345 | `lib/features/entries/presentation/widgets/entry_contractors_section.dart` | Split to list + header `_section` files |
| 325 | `lib/features/entries/presentation/screens/entry_editor_screen.dart` | Move build sections → `entry_editor_sections.dart` |
| 314 | `lib/features/entries/presentation/widgets/entry_contractors_section_actions.dart` | Split action branches into `_actions` variants |
| 307 | `lib/features/entries/presentation/controllers/entry_editing_controller.dart` | Extract sub-controllers via composition |

### Step 3.3 — Batch Settings + Sync + Analytics + Dashboard

| Lines | File | Strategy |
|---:|---|---|
| 560 | `lib/features/settings/presentation/screens/app_lock_settings_screen.dart` | Split into privacy / biometric / pin `_section` widgets |
| 478 | `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` | Hoist conflict rendering → `conflict_viewer_sections.dart` |
| 469 | `lib/features/settings/presentation/screens/consent_screen.dart` | Move markdown body → `consent_body_content.dart`; screen is scaffold only |
| 467 | `lib/features/analytics/presentation/screens/project_analytics_screen.dart` | Hoist remaining chart sections → `project_analytics_sections.dart` |
| 440 | `lib/features/settings/presentation/screens/edit_profile_screen.dart` | Split into identity / preferences `_section` widgets |
| 436 | `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` | Hoist diagnostics / tools / user-mgmt → `admin_dashboard_sections.dart` |
| 428 | `lib/features/pay_applications/presentation/dialogs/pay_app_date_range_dialog.dart` | Split picker + preview into separate widgets |
| 383 | `lib/features/sync/presentation/widgets/sync_dashboard_status_widgets.dart` | Split by status-type (queue / errors / recent) |
| 373 | `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | Hoist grid + rail → `project_dashboard_sections.dart` |
| 363 | `lib/features/settings/presentation/widgets/admin_dashboard_widgets.dart` | Split per card |
| 355 | `lib/features/settings/presentation/screens/help_support_screen.dart` | Hoist FAQ + contact sections |
| 354 | `lib/features/sync/presentation/support/conflict_presentation_mapper.dart` | Split mapping functions to `_helpers.dart` family |
| 337 | `lib/features/auth/presentation/providers/app_config_provider.dart` | Split provider composition by config-domain mixins |
| 320 | `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart` | Split per diagnostic group |
| 315 | `lib/features/todos/presentation/screens/todos_screen.dart` | Hoist filter bar + list |
| 304 | `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` | Hoist preview section → `pdf_import_preview_sections.dart` |
| 301 | `lib/features/analytics/presentation/providers/project_analytics_provider.dart` | Split per-metric compute into `_helpers.dart` |

### Step 3.4 — Batch Remaining (quantities, projects, pay-app screens)

| Lines | File | Strategy |
|---:|---|---|
| 669 | `lib/features/quantities/presentation/widgets/quantities_pay_app_export_flow.dart` | Split export phases: `quantities_pay_app_export_prep_section.dart`, `_generate_section.dart`, `_finalize_section.dart`; actions via `_actions` variant |
| 384 | `lib/features/projects/presentation/widgets/project_contractors_tab_body.dart` | Hoist modes into dedicated widgets |
| 370 | `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart` | Split header / line-item grid / footer → `pay_app_detail_sections.dart` |
| 329 | `lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart` | Hoist comparison table |

**Reconciliation to 45 (closes completeness-review finding):** the four batches above enumerate 44 distinct files (pay-app date-range dialog duplicate removed). The 45th file surfaces dynamically — `pwsh -File scripts/audit_ui_file_sizes.ps1` at Phase 3 entry produces the authoritative list; any file not in this plan's tables but flagged by the script gets decomposed under the same rules. The commit message for each Phase 3 batch cites the audit script's pre- and post-commit output.

**Rules across Phase 3:**

- Preserve user-visible behavior. Logic changes are separate commits.
- No new state management.
- Every `mounted` guard survives the split.
- `scripts/audit_ui_file_sizes.ps1` green at the end of each batch.

**Verify:**

```
pwsh -File scripts/audit_ui_file_sizes.ps1
flutter analyze
dart run custom_lint
```

---

## Phase 4: Rubric Items 6-10 Dynamic Sweep

Closes the gap the reviewers flagged: rubric items 6 (wiring integrity), 7 (`go_router` compliance), 8 (back behavior), 9 (responsive), 10 (mounted guard) have no authoring step elsewhere. This phase covers them across the 57-screen surface.

### Step 4.1 — Item 7: `go_router` compliance + widget-key cleanup

**Known live violation (from tailor ground-truth):** `lib/core/router/routes/project_routes.dart:28-30` uses `ValueKey(projectId)` as the widget key for the project-edit route. Replace with a factory `TestingKeys.projectEditScreen(projectId)` sentinel (add `static Key projectEditScreen(String id) => Key('project_edit_screen_$id')` in `projects_keys.dart`; re-export from facade).

**Sweep:** Grep for `Navigator\.(push|pushNamed|pop|pushReplacement)` under `lib/features/*/presentation/`. Each hit must either:

1. Route through `context.go`, `context.push`, or `context.goNamed` (`go_router` API), or
2. Be a documented modal dismissal that `go_router` does not own (e.g. `Navigator.of(context, rootNavigator: true).pop()` inside a dialog).

Any ambiguous hit becomes a remediation commit — replace with the `go_router` equivalent or add a short comment citing the reason it stays on raw navigator.

### Step 4.2 — Item 10: Mounted guard sweep

Grep for `await` within `State<…>` / provider methods where the next line touches `context` without a `mounted` check in between. This is a lint-augmented review: `custom_lint` + analyzer warning `use_build_context_synchronously` already surfaces most; remaining offenders (false-negatives due to indirect `context` access via `Provider.of` or `read`) are remediated by hand with a guard `if (!mounted) return;`.

### Step 4.3 — Item 6: Wiring integrity

For each presentation file that constructs a provider inline or calls a repository/use-case directly, migrate the wiring to the matching `di/*screen_providers.dart`. Audit anchor: `grep -Rn "_.*Datasource\|_.*Repository\|_.*UseCase" lib/features/*/presentation/` — any ad-hoc construction in `presentation/` is a rubric item 6 failure and moves to `di/`.

### Step 4.4 — Item 8: Back behavior assertion source

Every screen registered in `screenContracts` (after Phase 5 expansion) must have its `back_at_root` assertion point defined: when the back stack is empty, the screen calls `context.go('/')` (or the feature's declared entry route) instead of stranding the back stack. Implementation pattern: `router.canPop` check exists in `driver_interaction_handler_navigation_routes.dart:90` — the screen's `WillPopScope` / `PopScope` handler uses the same semantic. Sweep: grep for `PopScope` / `WillPopScope` usage on every sync-visible screen in Phase 5; screens lacking one get one added if `back_at_root` is in their sub-flow set.

### Step 4.5 — Item 9: Responsive audit

No code sweep — this rubric item is enforced by the Phase 7.4 matrix gate running every in-matrix sub-flow on both S21 (360dp) and S10 (~800dp). The plan records explicitly: the matrix gate is the responsive-rubric enforcer.

**Verify for Phase 4:**

```
flutter analyze
dart run custom_lint
```

Must be green with zero remaining `Navigator.push` offenders in `presentation/`, zero unguarded async-gap `context` uses surfaced by the analyzer, and all ad-hoc datasource wiring moved to `di/`. `custom_lint` catches the `use_build_context_synchronously` subset automatically.

---

## Phase 5: Sentinel Keys + Screen Contract Expansion

Rubric item 3 (one `TestingKeys.*` sentinel per screen) and rubric item 11 (sync-visible screens in `screenContracts`). Atomic with Phase 6 — contracts reference sub-flow YAML, YAML references sentinels.

### Step 5.1 — Add missing sentinel keys to per-feature key files

For every `screenRegistry` entry without a sentinel in its owning `<feature>_keys.dart`, add one (literal = snake_case of screen id) and re-export from `lib/shared/testing_keys/testing_keys.dart` facade.

**Additions (authoritative, based on the 17-module facade — see Phase 2.1 for the 4 new modules added):**

- `auth_keys.dart`: `loginScreen`, `registerScreen`, `forgotPasswordScreen`, `otpVerificationScreen`, `updatePasswordScreen`, `updateRequiredScreen`, `profileSetupScreen`, `companySetupScreen`, `pendingApprovalScreen`, `accountStatusScreen`.
- `entries_keys.dart`: confirm `entriesListScreen`, `reviewScreen`, `reviewSummaryScreen`, `draftListScreen`, `entryEditorScreen`, `entryPdfPreviewScreen`, `homeScreen`. (`HomeScreen` sentinel lives here since the screen file is in `lib/features/entries/presentation/screens/home_screen.dart`.)
- `projects_keys.dart`: `projectListScreen`, `projectSetupScreen`, `projectSetupNewScreen`, `projectSetupEditScreen` (plus the factory key `projectEditScreen(String id)` from Phase 4.1), `projectDashboardScreen` (lives under dashboard feature but key stays in projects module since the screen composes projects data — writer spot-checks at execution time and moves to `dashboard_keys.dart` if a dedicated module already exists; otherwise keep under projects).
- `settings_keys.dart`: `settingsScreen`, `editProfileScreen`, `trashScreen`, `adminDashboardScreen`, `personnelTypesScreen`, `appLockSettingsScreen`, `appLockUnlockScreen`, `savedExportsScreen`, `legalDocumentScreen`, `ossLicensesScreen`, `helpSupportScreen`, `consentScreen`.
- `toolbox_keys.dart`: `toolboxHomeScreen`, `calculatorScreen`, `todosScreen`.
- `gallery_keys.dart` (new this phase, per Phase 2.1): `galleryScreen`.
- `pay_app_keys.dart`: `payAppDetailScreen`, `contractorComparisonScreen`.
- `sync_keys.dart`: already holds `syncDashboardScreen`, `conflictViewerScreen` — confirm.
- `contractors_keys.dart`: `contractorSelectionScreen`.
- `quantities_keys.dart`: `quantitiesScreen`, `quantityCalculatorScreen`.
- `forms_keys.dart` (new per Phase 2.1): `mdotHubScreen`, `formNewDispatcherScreen`, `mdot1126FormScreen`, `mdot1174rFormScreen`, `formFillScreen`, `formViewerScreen`, `formGalleryScreen`, `formPdfPreviewScreen`, `proctorEntryScreen`, `quickTestEntryScreen`, `weightsEntryScreen`.
- `pdf_keys.dart` (new per Phase 2.1): `pdfImportPreviewScreen`, `mpImportPreviewScreen`.
- `analytics_keys.dart` (new per Phase 2.1): `projectAnalyticsScreen`.

Every new sentinel must have a matching facade delegation in `testing_keys.dart` (`static const fooScreen = FeatureTestingKeys.fooScreen;` for const values; `static Key fooScreen(String id) => FeatureTestingKeys.fooScreen(id);` for factory keys).

### Step 5.2 — Expand `screenContracts`

For each sync-visible screen currently missing a contract, add a `ScreenContract` entry with `rootKey: TestingKeys.<sentinel>`, the full `routes:` list it serves, `actionKeys:` for interactive widgets used by sub-flows, and `stateKeys:` for assertion targets.

**New contracts (sync-visible or referenced by `deep_link_entry`):**

- `LoginScreen` — routes `['/login']`; `actionKeys: ['login_email_field', 'login_password_field', 'login_submit_button']`.
- `ProjectDashboardScreen` — routes `['/']` (shell index surface); `stateKeys: ['project_dashboard_screen']`.
- `EntryEditorScreen`, `EntryEditorCreateScreen`, `EntryEditorReportScreen` — routes `['/entry/:projectId/:date']`, `['/report/:entryId']`; `seedArgs: ['projectId', 'date']` matching `screenRegistry`.
- `ProjectSetupScreen`, `ProjectSetupNewScreen`, `ProjectSetupEditScreen` — routes `['/project/new', '/project/:projectId/edit']`.
- `QuantityCalculatorScreen` — routes `['/quantity-calculator/:entryId']`.
- `ToolboxHomeScreen` — routes `['/toolbox']`.
- `QuickTestEntryScreen`, `ProctorEntryScreen`, `WeightsEntryScreen` — routes under `/form/new/:formId`; `seedArgs: ['formId', 'projectId']`.
- `CalculatorScreen` — routes `['/calculator']`.
- `GalleryScreen` — routes `['/gallery']`.
- `TodosScreen` — routes `['/todos']`.
- `EditProfileScreen` — routes `['/edit-profile']`.
- `AdminDashboardScreen` — routes `['/admin-dashboard']`; `stateKeys: ['admin_dashboard_screen']`.
- `SettingsScreen` — routes `['/settings']` (confirm path at execution time from `settings_routes.dart`).
- `ProjectAnalyticsScreen` — routes `['/analytics/:projectId']`; `seedArgs: ['projectId']`.

**Rules (from tailor `screen-contract-registration.md`):**

- `ScreenContract.rootKey` is a typed `TestingKeys.*` — no string literal.
- `actionKeys` / `stateKeys` are string literals matching the sentinel's raw value; factory-key templates use `<placeholder>` format (e.g. `'project_download_button_<projectId>'`).
- `screenRegistry.seedArgs ⊆ screenContracts.seedArgs` where both exist.
- `HomeScreen` stays rubric-only — no contract (shell index, not a sync-visible terminal surface).

### Step 5.3 — Extend `flowRegistry` per concern

Add `FlowDefinition` entries to the correct per-concern file. Example for a new `deep_link_entry` flow:

```dart
// lib/core/driver/flows/navigation_flow_definitions.dart
const payAppDeepLinkEntry = FlowDefinition(
  name: 'pay_app_deep_link_entry',
  routes: [],                                       // resolved by go_router dispatch
  defaultInitialLocation: '/pay-app/harness-pay-app-001',
  seedScreens: ['PayApplicationDetailScreen'],      // must exist in screenRegistry
);
```

- `lib/core/driver/flows/forms_flow_definitions.dart` — new entries for `form_completeness`, `export_verification` against each form screen.
- `lib/core/driver/flows/navigation_flow_definitions.dart` — new entries for `nav_bar_switch_mid_flow`, `deep_link_entry`, `tab_switch_mid_edit`, `back_at_root`, `backward_traversal`, `orientation_change` — one `FlowDefinition` per (sub-flow, target-screen) pair.
- `lib/core/driver/flows/verification_flow_definitions.dart` — new entries for `role_restriction` per role gate.

**Rule:** `FlowDefinition.seedScreens` must reference an existing `screenRegistry` key; the Phase 1.7 guard test asserts this at CI time.

**Verify for Phase 5:**

```
flutter analyze
dart run custom_lint
flutter test test/core/driver/registry_alignment_test.dart
```

Must be green before Phase 6 feature files begin referencing contracts.

---

## Phase 6: Feature Spec Authoring

Sixteen `.claude/test-flows/features/*.md` files. Each file follows the spec § Per-Feature `.md` Template. Because the spec states migration runs in parallel, per-feature authoring can be agent-fanned-out — but each file's commit still lands with its sentinel keys (Phase 5), contracts (Phase 5), and retired flow IDs together.

### Authoring rules (apply to all 16 files)

1. Header: `# Feature: <name>` matches the taxonomy column.
2. `## Purpose`: one paragraph.
3. `## Screens`: bullet list `<screen_name>: <file path>` (verbatim paths, verified to exist).
4. `## Preconditions catalog`: every name referenced by `requires:` in the sub-flow YAML, with a short description. Names match `driver_seed_handler.dart` `_dispatchPrecondition` switch.
5. `## Sub-flows`: single fenced ```yaml block at the `## Sub-flows` heading. Validator parses exactly this block.
6. Sub-flow `name` from the ten-name catalog; omitted = N/A per spec § Sub-flow Catalog collapse rule. Role-gated features MUST include a `role_restriction` sub-flow; the validator enforces this.
7. Every `tap`/`text`/`wait`/`find` references a sentinel literal in `lib/shared/testing_keys/*.dart`. Factory keys render as `'<kind>_<subject>_<placeholder>'`.
8. Every `navigate` / `current_route` literal matches a `go_router` path; `/sync/conflicts` declares `kDebugMode`-only collapse.
9. `## Retired flow IDs`: bullet list populated from spec § Old-Tier → New-Feature Mapping + the M01-M13 table in Phase 1.8. Every ID in the flow-dependencies index lands in exactly one feature block (or is marked out-of-scope: S01-S21, P06).

### Per-feature sub-flow applicability matrix (closes completeness-review finding)

Each feature MUST declare at minimum the sub-flows marked `Y` below. Sub-flows marked `N/A` are explicitly collapsed-by-omission and the validator accepts their absence. This matrix is the reference — the validator runs against it (`tools/validate_feature_spec.py --check-applicability`).

| Feature | forward_happy | backward_traversal | nav_bar_switch_mid_flow | back_at_root | deep_link_entry | tab_switch_mid_edit | orientation_change | form_completeness | export_verification | role_restriction |
|---|---|---|---|---|---|---|---|---|---|---|
| auth | Y | Y | N/A | Y | Y | N/A | Y | N/A | N/A | N/A |
| dashboard | Y | Y | Y | Y | Y | N/A | Y | N/A | N/A | N/A |
| projects | Y | Y | Y | Y | Y | Y | Y | N/A | N/A | Y (inspector) |
| entries | Y | Y | Y | Y | Y | Y | Y | N/A | Y | Y (inspector) |
| forms | Y | Y | Y | Y | Y | Y | Y | Y | Y | N/A |
| pay_applications | Y | Y | Y | Y | Y | N/A | Y | N/A | Y | Y (inspector) |
| quantities | Y | Y | Y | Y | Y | Y | Y | N/A | Y | N/A |
| analytics | Y | Y | Y | Y | Y | N/A | Y | N/A | Y | Y (inspector) |
| pdf | Y | Y | N/A | Y | Y (or N/A — see §pdf note) | N/A | Y | N/A | Y | Y (inspector) |
| gallery | Y | Y | Y | Y | Y | N/A | Y | N/A | N/A | N/A |
| toolbox | Y | Y | Y | Y | Y | N/A | Y | N/A | N/A | N/A |
| calculator | Y | Y | Y | Y | Y | Y | Y | N/A | N/A | N/A |
| todos | Y | Y | Y | Y | Y | Y | Y | N/A | N/A | N/A |
| settings | Y | Y | Y | Y | Y | N/A | Y | N/A | Y (saved-exports) | Y (non-admin denied admin surfaces) |
| sync_ui | Y | Y | Y | Y | Y (debug-only for conflicts) | N/A | Y | N/A | N/A | N/A |
| contractors | Y | Y | Y | Y | Y | N/A | Y | N/A | N/A | N/A |

### Files to create (invariants; detailed YAML authored at execution time)

- `.claude/test-flows/features/auth.md` — inherits T01-T04, M01, M02. Roles: all. Auth sub-flows testing OTP / pending-approval / account-status MUST use `pending_profile` / `otp_required_profile` / `rejected_profile` preconditions, NOT `base_data` (closes security-review finding on approval bypass).
- `.claude/test-flows/features/dashboard.md` — absorbs the dashboard/home nav subset of T92-T96. Roles: all. `HomeScreen` referenced in `## Screens` but file ownership note: "`HomeScreen` is registered under the entries feature (`lib/features/entries/presentation/screens/home_screen.dart`) and stays owned there; this feature file tests its home-tab composition only."
- `.claude/test-flows/features/projects.md` — inherits T05-T14 + archive subset of T53-T58, M07. Roles: `[admin, engineer, officeTechnician]` for mutations + `role_restriction` with `[inspector]` asserting read-only on project-setup. `deep_link_entry` targets `/project/:projectId/edit`.
- `.claude/test-flows/features/entries.md` — inherits T15-T30 + entry subset of T59-T77, M05, M12, M13. `forward_happy` on `[admin, engineer, officeTechnician]`; `role_restriction` with `[inspector]` asserts read-only on entry-editor. `deep_link_entry` targets `/entry/:projectId/:date`.
- `.claude/test-flows/features/forms.md` — inherits T35-T37, T43, T74, M09. Roles: all. Sub-flows per form type (`mdot_1126`, `mdot_1174r`, `form_gallery`, `form_fill`). `form_completeness` + `export_verification` reference the `PdfAcroFormInspector` via assertion verbs `pdf_fields_populated` and `pdf_is_acroform` (defined in `patterns/feature-spec-markdown.md`).
- `.claude/test-flows/features/pay_applications.md` — inherits P01-P05. P06 out of scope. Roles: `[admin, engineer, officeTechnician]` + `role_restriction` with `[inspector]`.
- `.claude/test-flows/features/quantities.md` — inherits quantities subset of T15-T30. Roles: all.
- `.claude/test-flows/features/analytics.md` — roles: `[admin, engineer, officeTechnician]` + `role_restriction` with `[inspector]`. `deep_link_entry` targets `/analytics/:projectId`.
- `.claude/test-flows/features/pdf.md` — inherits M03, M04 (PDF import manual flows absorbed). Spec § Old-Tier mapping says T41-T42 go to owning features' `export_verification`; `pdf.md` does NOT claim T41-T42 — they go under whichever feature's PDF gets exported. Roles: `[admin, engineer, officeTechnician]` + `role_restriction` with `[inspector]`. **§pdf note:** `deep_link_entry` to `/import/preview/:projectId` depends on Phase 1.3's `pdf_import_result_staged` precondition; if the precondition successfully stages `state.extra`, `deep_link_entry` is `Y`, else the feature file declares `deep_link_entry` as N/A (collapse-by-omission) and documents the reason in the feature's Purpose section.
- `.claude/test-flows/features/gallery.md` — inherits T40. Roles: all.
- `.claude/test-flows/features/toolbox.md` — inherits toolbox nav IDs. Roles: all.
- `.claude/test-flows/features/calculator.md` — inherits T38-T39. Roles: all. Sub-flows for HMA + concrete tabs.
- `.claude/test-flows/features/todos.md` — inherits T31-T34. Roles: all.
- `.claude/test-flows/features/settings.md` — inherits T44-T58, M08, M10, M11. `role_restriction` asserts admin-only denial on admin-dashboard, personnel-types, trash for `[engineer, officeTechnician, inspector]`. `export_verification` covers saved-exports.
- `.claude/test-flows/features/sync_ui.md` — inherits T85-T91 UX subset only. **Scope clarification (closes completeness-review finding):** sub-flows cover UX/nav only; no assertions against `SyncCoordinator` / `SyncErrorClassifier` / `SyncStatus` transport state. Sync transport stays covered by dual-device S01-S21 flows (out of scope for this refactor). Conflict-viewer sub-flows declare `kDebugMode`-only collapse.
- `.claude/test-flows/features/contractors.md` — inherits contractor subset of T59-T77. Roles: all.

### Migration parallelism rules (resolves spec open question #7)

- Each feature migration is a self-contained commit: feature `.md` + sentinel keys + screen contracts + flow definitions + retired IDs + any per-feature seeder addition in `harness_seed_data.dart`.
- Gate per commit: `flutter analyze`, `scripts/audit_ui_file_sizes.ps1`, `dart run custom_lint`, `python tools/validate_feature_spec.py --feature <name>`, `flutter test test/core/driver/registry_alignment_test.dart`.
- Agents coordinate by claiming a feature via task ordering. Shared files (`testing_keys.dart` facade, `screen_contract_registry.dart`, `flow-dependencies.md` index, `harness_seed_data.dart` switch) serialize through task ordering; if contention occurs, fall back to sequential commits — in practice, expect sequential.
- No feature cuts over with `fixme:` or `skip:` in sub-flow YAML unless explicitly approved in commit message body.

**Verify for Phase 6 (per feature):**

```
flutter analyze
dart run custom_lint
flutter test test/core/driver/registry_alignment_test.dart
python tools/validate_feature_spec.py --feature <name>
```

---

## Phase 7: Old Tier Retirement & Final Gate

Only runs after every feature's commit in Phase 6 is landed and all old IDs are assigned in the rewritten `flow-dependencies.md` index.

### Step 7.1 — Delete retired tier files

**Files to delete:**

- `.claude/test-flows/tiers/setup-and-auth.md`
- `.claude/test-flows/tiers/entry-crud.md`
- `.claude/test-flows/tiers/toolbox-and-pdf.md`
- `.claude/test-flows/tiers/pay-app-and-exports.md`
- `.claude/test-flows/tiers/settings-and-admin.md`
- `.claude/test-flows/tiers/mutations.md`
- `.claude/test-flows/tiers/verification.md`
- `.claude/test-flows/tiers/manual-flows.md` — all M-IDs absorbed per Phase 1.8 table; no sync-only survivors.

### Step 7.2 — Verify retirement completeness

```
python tools/validate_retired_flow_ids.py
```

Must exit 0. Every ID in the pre-rewrite `flow-dependencies.md` (T01-T96, P01-P06, M01-M13) appears in exactly one feature's `Retired flow IDs` block or is marked out-of-scope (S01-S21, P06).

### Step 7.3 — Full rubric gate

```
flutter analyze
dart run custom_lint
pwsh -File scripts/audit_ui_file_sizes.ps1
python scripts/validate_sync_adapter_registry.py
python tools/validate_feature_spec.py --all
python tools/validate_retired_flow_ids.py
flutter test test/core/driver/registry_alignment_test.dart test/support/pdf_acroform_inspector_test.dart test/core/driver/driver_seed_handler_test.dart
```

All green. Any scripted spec numbers that differ from tailor baselines (166 `Colors` occurrences → 0, 10 hardcoded Keys → 0, 45 file-size violations → 0) surface as a burn-down delta in the final commit message. Any residual delta is a rubric failure, not a negotiation.

### Step 7.4 — Matrix gate

For every feature file, run the in-matrix sub-flows against both S21 and S10 via the existing driver loop. Selector grammar from Phase 1.9:

```
/test <feature> --device s21        # runner iterates appliesTo.roles
/test <feature> --device s10        # runner iterates appliesTo.roles
```

Per-role iteration is automatic when `--role` is omitted; the runner captures per-(sub-flow, role, device) pass/fail under `.claude/test-results/<timestamp>_<feature>/`. Any failure is either:

1. A real production bug — fix committed to the same PR, regression-locked as sub-flow coverage.
2. A spec gap — escalate to user for a spec amendment; do not weaken the rubric.

### Step 7.5 — Confirm flagged-gap closure

- Spec OQ #1 (`/driver/seed` body) — closed by Phase 1.2 (precondition-keyed).
- Spec OQ #2 (PDF helper) — closed by Phase 1.4.
- Spec OQ #3 (sentinel naming + contract scope) — closed by Phase 5.1 + 5.2 (sync-visible + `deep_link_entry` targets).
- Spec OQ #4 (YAML schema + validator) — closed by Phase 1.5 (`tools/validate_feature_spec.py`).
- Spec OQ #5 (retirement bookkeeping) — closed by Phase 1.6 + 1.8 + Phase 6 per-feature + Phase 7.2 audit.
- Spec OQ #6 (registry automation) — closed by Phase 1.7 Dart guard test.
- Spec OQ #7 (migration parallelism) — closed by Phase 6 rules.
- Spec OQ #8 (`/sync/conflicts` kDebugMode) — closed by Phase 6 `sync_ui.md` collapse note.
- Tailor gaps #1-#8 — closed by the corresponding phase steps (documented in the plan body above).

Every flagged gap must have a commit-level artifact proving closure. If any gap is still open, escalate — do not merge.

### Step 7.6 — Open PR on `gocr-integration`

Single PR per spec § Blast Radius Budget → Rollback. PR body summarizes:

- Rubric burn-down: colors 166 → 0, hardcoded keys 10 → 0, file-size violations 45 → 0, rubric-item-6/7/8/10 live violations (starting with `ValueKey(projectId)`) → 0.
- 16 feature files authored + 7 tier files + 1 manual-flows tier file deleted.
- New `/driver/seed` endpoint + extracted `driver_http_guards.dart` + `PdfAcroFormInspector` (test-scope) + `validate_feature_spec.py` + `validate_retired_flow_ids.py` + registry guard test.
- All 8 spec open questions + 8 tailor flagged gaps closed with commit-level artifacts.

No feature flag. Test infra is low-risk at runtime per spec.
