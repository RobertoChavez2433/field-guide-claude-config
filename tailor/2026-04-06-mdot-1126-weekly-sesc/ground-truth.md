# Ground Truth

All literals, paths, and symbol names referenced by the spec, verified against the current codebase (commit `23cf79f6`).

## Verified — Existing Symbols & Paths

### Forms Feature

| Literal | Source | Status |
|---|---|---|
| `lib/features/forms/data/registries/builtin_forms.dart` | exists | VERIFIED |
| `builtinForms` constant (list) | `builtin_forms.dart:6` | VERIFIED |
| `BuiltinFormConfig` class | `lib/features/forms/data/registries/builtin_form_config.dart:5` | VERIFIED |
| Fields: `id, name, templatePath, registerCapabilities` + `toInspectorForm()` | same file lines 5–25 | VERIFIED |
| `FormScreenRegistry.instance` (singleton) | `form_screen_registry.dart:13` | VERIFIED |
| `FormScreenBuilder` typedef `({formId, responseId, projectId})` → `Widget` | `form_screen_registry.dart:7` | VERIFIED |
| `FormPdfFillerRegistry.instance` | `form_pdf_filler_registry.dart:11` | VERIFIED |
| `PdfFieldFiller` typedef `(responseData, headerData) → Map<String,String>` | `form_pdf_filler_registry.dart:6` | VERIFIED |
| `FormValidatorRegistry.instance` | `form_validator_registry.dart:8` | VERIFIED |
| `FormValidator` typedef `(responseData, headerData) → List<String>` | `form_validator_registry.dart:5` | VERIFIED |
| `FormInitialDataFactory.instance` | `form_initial_data_factory.dart:7` | VERIFIED |
| `InitialDataBuilder` typedef `() → Map<String,dynamic>` | `form_initial_data_factory.dart:5` | VERIFIED |
| `FormQuickActionRegistry.instance` | `form_quick_action_registry.dart:64` | VERIFIED |
| `FormQuickAction(icon,label,execute)` | `form_quick_action_registry.dart:9` | VERIFIED |
| `FormCalculatorRegistry.instance` (not needed for 1126) | `form_calculator_registry.dart:12` | VERIFIED |
| `registerMdot0582B()` exemplar function | `mdot_0582b_registrations.dart:9` | VERIFIED |
| `fillMdot0582bPdfFields()` exemplar | `mdot_0582b_pdf_filler.dart:9` | VERIFIED |
| `validateMdot0582B()` exemplar | `mdot_0582b_validator.dart:9` | VERIFIED |
| `kFormTypeMdot0582b = 'mdot_0582b'` | `form_type_constants.dart:11` | VERIFIED |
| `kFormTemplateMdot0582b = 'assets/templates/forms/mdot_0582b_form.pdf'` | `form_type_constants.dart:14` | VERIFIED |

### Form Response Model

| Literal | Source | Status |
|---|---|---|
| `FormResponse` class, `entryId` field | `form_response.dart:54` | VERIFIED |
| `FormResponse.copyWith(entryId: ...)` | `form_response.dart:121` | VERIFIED |
| `FormResponse.parsedResponseData` | `form_response.dart:203` | VERIFIED |
| `FormResponse.withResponseDataPatch(map)` | `form_response.dart:334` | VERIFIED |
| `FormResponseRepository.getResponsesForEntry(entryId)` | `form_response_repository.dart:14` | VERIFIED |

### Entries / Export

| Literal | Source | Status |
|---|---|---|
| `ExportEntryUseCase.call(entryId, {currentUserId})` | `export_entry_use_case.dart:16` | VERIFIED |
| `DailyEntryRepository.getByDate(projectId, date)` | `daily_entry_repository.dart:9` | VERIFIED |
| `DailyEntryRepository.create(entry)` | `daily_entry_repository.dart:84` | VERIFIED |

### Database / Schema

| Literal | Source | Status |
|---|---|---|
| Schema version = **53** (not 50 as CLAUDE.md suggests, not 52) | `database_service.dart:69,110` | VERIFIED |
| `SupportTables` pattern exemplar | `schema/support_tables.dart:7` | VERIFIED |
| Schema dir: `lib/core/database/schema/` | ls verified | VERIFIED |
| `sync_engine_tables.dart` (change_log, sync_control) | `schema/sync_engine_tables.dart:5` | VERIFIED |
| `SchemaVerifier` runs on startup | `schema_verifier.dart:95` | VERIFIED |
| `SoftDeleteService.hardDeleteWithSync` | `soft_delete_service.dart:852` | VERIFIED |

### Sync Adapters

| Literal | Source | Status |
|---|---|---|
| `AdapterConfig` data class | `adapter_config.dart:13` | VERIFIED |
| `simpleAdapters` const list | `simple_adapters.dart:18` | VERIFIED |
| `ScopeType.viaProject` / `ScopeType.direct` | `adapter_config.dart` | VERIFIED |
| File-backed adapter exemplar: `form_exports` uses `isFileAdapter: true`, `storageBucket: 'form-exports'`, `buildStoragePath: _buildFormExportPath` | `simple_adapters.dart` | VERIFIED |
| `FileSyncHandler` handles 3-phase file upload, EXIF strip, path validation | `file_sync_handler.dart:26` | VERIFIED |

### Lint Rules (path-gated)

| Rule | Path gate | Applies to 1126 new files? |
|---|---|---|
| `no_raw_button` (A25) | `/presentation/`, `/shared/widgets/`, `/core/router/` | YES — signature pad, banner, card |
| `no_raw_divider` (A26) | same | YES |
| `no_raw_tooltip` (A27) | same | YES |
| `no_raw_dropdown` (A28) | same | YES |
| `no_raw_navigator` (A33) | same | YES |
| `no_hardcoded_spacing` (A30) | same | YES |
| `no_hardcoded_radius` | same | YES |
| `no_hardcoded_duration` | same | YES |
| `no_raw_snackbar` | same | YES |
| `no_raw_alert_dialog` (A18) | same | YES |
| `no_raw_show_dialog` (A19) | same | YES |
| `no_hardcoded_form_type` (A14) | all non-registry files | YES — must use a `kFormTypeMdot1126` constant |

All path checks use `replaceAll('\\', '/')` before `contains()` (verified in `no_raw_button.dart:40`).

## FLAGGED

| Item | Spec says | Reality | Action |
|---|---|---|---|
| **Schema version for new tables** | "schema v53" | Current schema = **53**; must bump to **54** | Plan must say v54, not v53 |
| **`lib/features/signatures/`** | Spec introduces new `signatures` feature module | No such directory exists today | Plan must create the feature dir with `data/models/`, `data/repositories/`, etc. |
| **Asset filename** | `assets/templates/forms/mdot_1126.pdf` | 0582B convention is `mdot_0582b_form.pdf` (has `_form` suffix) | Minor — plan should align to `mdot_1126_form.pdf` OR explicitly note deviation |
| **`TestingKeys.mdot1126*`** | References `TestingKeys.X` directly | Testing keys currently live in `lib/shared/testing_keys/testing_keys.dart` (single file). 0582B keys are in that root file. No `forms_keys.dart` exists | Plan must add 1126 keys to the existing `testing_keys.dart` OR create a new per-feature `forms_keys.dart` (matches other features like `entries_keys.dart`) |

## Lint Rules for New Files

Every `lib/features/forms/presentation/**/*.dart` and `lib/features/forms/presentation/widgets/**/*.dart` file listed in the spec is subject to the full design-system rule set above. Key implications:

- `SignaturePadField` **MUST** wrap `signature` package canvas inside an `AppCard` / `AppSurface` with design tokens — no raw `Container` sizing literals.
- `WeeklySescReminderBanner` / `WeeklySescReminderCard` **MUST** use `AppBanner`/`AppCard`, never `Material`/`Container` with hardcoded spacing.
- All buttons (Sign, Clear, Add Rainfall, Add Measure, Attach, Save) **MUST** use `AppButton.primary/secondary/tertiary`.
- Tri-state checklist rows **MUST** use design-system chip/segmented control, not raw `ChoiceChip` without the DS wrapper.
- Add-new-measure + rainfall editors **MUST** use `AppTextField`, not raw `TextFormField`.
- Date pickers **MUST** go through the existing DS helper (not raw `showDatePicker`).

The new domain/data files under `lib/features/forms/domain/usecases/**` and `lib/features/signatures/data/**` are outside the presentation-scoped path gates, so the raw-widget rules do not apply there — but `no_hardcoded_form_type` (A14) still applies, which is why every `'mdot_1126'` literal must go through a new `kFormTypeMdot1126` constant in `form_type_constants.dart`.
