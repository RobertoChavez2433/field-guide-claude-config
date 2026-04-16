# Ground Truth

## Verified Literals

### Role gating (`lib/features/auth/data/models/user_role.dart`)

| Getter | Value | Notes |
|---|---|---|
| `UserRole.isAdmin` | `this == admin` | Admin-only surfaces collapse rule |
| `UserRole.canManageProjects` | `admin ∨ engineer ∨ officeTechnician` | Project-management collapse rule in spec |
| `UserRole.canEditFieldData` | `true` for all four roles | All roles edit field data (inspector read-only for project-setup only) |
| `UserRole.canManageProjectFieldData` | alias of `canEditFieldData` | Same as field-data |
| Enum values | `admin, engineer, officeTechnician, inspector` | Matches Supabase CHECK |
| `UserRole.wireName` | `admin`, `engineer`, `office_technician`, `inspector` | Supabase wire values |

The spec's matrix `roles: [admin, engineer, officeTechnician, inspector]` is exactly correct.

### Driver endpoints currently registered

`DriverShellRoutes` — `/driver/ready`, `/driver/find`, `/driver/screenshot`, `/driver/tree`, `/driver/hot-restart`.

`DriverInteractionRoutes` — `/driver/tap`, `/driver/tap-text`, `/driver/drag`, `/driver/text`, `/driver/scroll`, `/driver/scroll-to-key`, `/driver/back`, `/driver/wait`, `/driver/navigate`, `/driver/dismiss-keyboard`, `/driver/dismiss-overlays`, `/driver/current-route`.

`DriverDataSyncRoutes` — `/driver/sync`, `/driver/reset-integrity-check`, `/driver/local-record`, `/driver/change-log`, `/driver/create-record`, `/driver/inject-sync-poison`, `/driver/update-record`, `/driver/run-sync-repairs`, `/driver/sync-status`, `/driver/remove-from-device`, `/driver/restore-project-remote`.

Also present: `/driver/inject-file` (file injection), design-system diagnostics, delete-propagation. No `/driver/seed` or `/driver/set-screen-v2`. The spec's "HarnessSeedData.seedBaseData + seedScreenData" path is already wired, so `/driver/seed` is a new HTTP shell around existing seeding code.

### Registry surface counts

- `screenRegistryEntries` — 36 keys (screen_registry.dart).
- `screenContracts` — 16 keys (screen_contract_registry.dart). Gap: 20 screens in `screenRegistry` lack a contract entry. Any screen declared as `sub-flow: sync-visible` in a feature spec must land a contract here.
- `flowRegistry` — union of three per-concern maps. Entry point: `lib/core/driver/flows/flow_definition.dart`.

### Route literals (go_router)

All routes named in the spec were verified to exist:
- `/login`, `/register`, `/forgot-password`, `/verify-otp`, `/update-password`, `/update-required`, `/consent`, `/profile-setup`, `/company-setup`, `/pending-approval`, `/account-status` (auth).
- `/project/new`, `/project/:projectId/edit`, `/quantities`, `/quantity-calculator/:entryId` (projects).
- `/entries`, `/drafts/:projectId`, `/entry/:projectId/:date`, `/report/:entryId`, `/review`, `/review-summary`, `/personnel-types/:projectId` (entries).
- `/forms`, `/form/new/:formId`, `/form/:responseId`, `/import/preview/:projectId`, `/mp-import/preview/:projectId` (forms + pdf).
- `/toolbox`, `/calculator`, `/gallery`, `/todos` (toolbox).
- `/edit-profile`, `/admin-dashboard`, `/help-support`, `/legal-document`, `/oss-licenses`, `/settings/trash`, `/settings/saved-exports` (settings).
- `/pay-app/:payAppId`, `/pay-app/:payAppId/compare`, `/analytics/:projectId` (pay_app + analytics).
- `/sync/dashboard`, `/sync/conflicts` (sync).

**Flagged**: `/sync/conflicts` is only registered when `kDebugMode`. Feature spec `sync_ui.md` must include a note that conflict-viewer sub-flows are unreachable in release builds.

### PDF AcroForm capability

- `pubspec.yaml` already depends on `syncfusion_flutter_pdf: ^32.1.25`.
- Existing reader/writer code: `lib/features/forms/data/services/form_pdf_field_writer.dart` (uses `form.fields[i]`, `field.name`, `PdfTextBoxField.text`, `PdfTextBoxField.readOnly`).
- Existing read-back test: `test/features/forms/services/form_pdf_field_writer_test.dart` re-opens the saved PDF with `PdfDocument(inputBytes: savedBytes)` and reads `field.text` and raw `/V` via `PdfTextBoxFieldHelper.getHelper(...).dictionary?[PdfDictionaryProperties.v]`.

The spec's `PDF AcroForm inspection helper` can therefore be built on syncfusion. The "commercial license concern" note in the spec is already moot — the license has been accepted for production use.

Needed capabilities already reachable:
- Enumerate fields: `for (var i = 0; i < form.fields.count; i++) form.fields[i]`
- Read field name: `field.name`
- Read value: `field is PdfTextBoxField → field.text`; checkboxes/combos/lists have their own subclasses (`PdfLoadedCheckBoxField`, `PdfLoadedComboBoxField`, `PdfLoadedListBoxField`, `PdfLoadedRadioButtonListField`).
- Detect flatten: exported document still has `document.form.fields.count > 0`; if zero, it was flattened.

No new dependency is required.

### 300-line audit

`scripts/audit_ui_file_sizes.ps1` uses `MaxLines=300` and scans `lib/core/design_system` + `lib/features` for files whose path contains `presentation|design_system|widgets|screens|controllers|providers`. Current live failure count: **45 files**. Top offenders include `mdot_1174r_form_screen.dart` (677), `entry_review_screen.dart` (565), `app_lock_settings_screen.dart` (560), `form_gallery_screen.dart` (525). Blast radius list in this tailor directory carries the full set.

### Rubric status against live code (rule-sourced items)

| Rubric item | Counter (live) | Source |
|---|---|---|
| 1. Design tokens (no raw `Colors.*` in presentation) | **166 occurrences across 107 files** | `grep Colors\. lib/features/**/presentation/**/*.dart` |
| 2. No hardcoded `Key('…')` in presentation | **10 occurrences across 5 files** (not `_screen.dart`, widget/controller files) | `grep Key\\('` in presentation |
| 4. File-size ceiling 300 lines | **45 violations** | `scripts/audit_ui_file_sizes.ps1` |
| 7. `go_router` compliance | 1 live violation found during ground-truth: `/project/:projectId/edit` uses `ValueKey(projectId)` (not `TestingKeys.*`) as widget key | `lib/core/router/routes/project_routes.dart:28-30` |

Spec wording "15 files currently fail" (Colors) and "8 files currently fail" (hardcoded keys) is **outdated**. The audit must re-count these during plan execution. Do not hard-code the spec numbers into the per-feature checklist.

## Flagged Gaps

1. **`/driver/seed` endpoint shape.** Not present. HarnessSeedData already supports `seedBaseData()` and `seedScreenData(screen, data)`. Simplest path: HTTP wrapper that accepts `{"preconditions": [{"name": "project_draft", "args": {...}}, …]}` and dispatches to named seeders. Alternative: per-feature factory registry mirroring `screenRegistry`. Writer must pick one; the spec defers it.
2. **Feature-spec YAML schema + validator.** No schema exists. Where the validator lives (`tools/` script vs. Dart unit test) is undecided. Recommend `tools/validate_feature_spec.py` following `tools/validate_sync_adapter_registry.py` prior art.
3. **Sentinel-key naming convention for screens without one.** 20 `screenRegistry` entries (e.g. `LoginScreen`, `CalculatorScreen`, `TodosScreen`, `EditProfileScreen`, `FormViewerScreen`, …) have no `screenContract` and therefore no asserted `rootKey`. Writer must decide whether each screen needs a contract **and** a `rootKey` sentinel, or whether `screenContract` membership is sub-flow-scoped (only "sync-visible" screens require it per rubric item 11).
4. **Pre-existing keys gap.** `screenContracts` lists several action keys as **string templates** (`project_download_button_<projectId>`). These are not typed `TestingKeys.*` references. The rubric permits factory keys like `TestingKeys.projectDownloadButton(id)` — writer must confirm the contract can reference factory keys or tolerate string placeholders.
5. **Retirement bookkeeping.** `flow-dependencies.md` currently enumerates 121 flow IDs. Per-feature `.md` files must list the retired IDs in a `Retired flow IDs` section. Spec open question #5 flags this as deferred to tailor — the template already exists (bottom of spec § Per-Feature `.md` Template). Writer must ensure no flow ID is dropped between the old chain and the feature cutover commit.
6. **Registry atomicity.** Three registries (`screenRegistry`, `screenContracts`, `flowRegistry`) must update together. No current codegen. Plan should either add a guard unit test asserting set equality (screenRegistry keys ⊇ screenContract keys for sync-visible screens) or commit policy. Spec open question #6 flags this as undecided.
7. **Manual/P-flow absorption.** `M01-M13` are described in `manual-flows.md`. Mapping from M-IDs to UX feature buckets is present in spec § Old-Tier → New-Feature Mapping but is a single-line "UX ones absorbed per feature; sync-only ones untouched" — writer must explicitly list which M-IDs move into `features/*.md` and which stay in `manual-flows.md`.
8. **Home vs Dashboard duplication.** `dashboard` feature spec includes both `project-dashboard` and `home`. Home is currently at `/` (shell index) and is not in `screenContracts`. Writer must decide whether `home` warrants a contract or stays rubric-checked only.

No other deferred spec questions (§ Open Questions / Deferred to Tailor #1–#7) are resolvable by reading code alone.
