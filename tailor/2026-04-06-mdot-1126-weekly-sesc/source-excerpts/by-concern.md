# Source Excerpts — By Spec Concern

## Concern: Register the builtin form (Spec §2, §5)

**Goal**: `mdot_1126` appears alongside `mdot_0582b` in every registry.

Files to touch (verified):
- `lib/features/forms/data/registries/form_type_constants.dart` — add constants (see `source-excerpts/by-file.md`)
- `lib/features/forms/data/registries/builtin_forms.dart` — append `BuiltinFormConfig`
- `lib/features/forms/data/registries/mdot_1126_registrations.dart` (NEW) — `registerMdot1126()`
- `lib/features/forms/data/pdf/mdot_1126_pdf_filler.dart` (NEW)
- `lib/features/forms/data/validators/mdot_1126_validator.dart` (NEW)

Reference implementations: see `patterns/builtin-form-registration.md`, `patterns/pdf-filler.md`, `patterns/validator.md`.

Screen registration is deferred to UI init — find where 0582B is currently bound (not `mdot_0582b_registrations.dart` since that file explicitly notes the deferral). Grep for `FormScreenRegistry.instance.register` to locate.

---

## Concern: Data model for signatures (Spec §2)

**Goal**: Two new tables live in SQLite and Supabase, synced as adapter entries.

Files (verified):
- `lib/core/database/schema/signature_tables.dart` (NEW) — `SignatureTables` class — see `patterns/schema-table.md`
- `lib/core/database/database_service.dart` — bump version 53→54 at lines 69 and 110, add to `_onCreate` (wire both tables + triggers + indexes), add `_onUpgrade` branch
- `lib/core/database/schema_verifier.dart` — register expected column sets for both tables (model on `SupportTables` registration)
- `lib/features/signatures/` (NEW feature module) — models, datasources, repositories
- `lib/features/sync/adapters/simple_adapters.dart` — add 2 `AdapterConfig` entries — see `patterns/sync-adapter-config.md`
- `supabase/migrations/20260408000000_signature_tables.sql` (NEW) — tables + RLS + realtime + storage bucket

Test helpers to update in lockstep:
- `test/features/projects/integration/project_lifecycle_integration_test.dart:587`
- `test/features/sync/engine/scope_revocation_cleaner_test.dart:152`
- `test/features/sync/adapters/adapter_config_test.dart` — add fixture rows
- `test/features/sync/characterization/characterization_push_skip_test.dart` — accept new tables

---

## Concern: Sign, verify, invalidate (Spec §2 signature flow, §5 use cases, §9 security)

**Goal**: Signing writes `signature_files` + `signature_audit_log` + stamps `signature_audit_id` into `form_response.response_data`. Editing a signed form clears the stamp.

Files (NEW, see `patterns/use-case.md` for sketches):
- `lib/features/forms/domain/usecases/sign_form_response_use_case.dart`
- `lib/features/forms/domain/usecases/invalidate_form_signature_on_edit_use_case.dart`
- `lib/features/signatures/data/models/signature_audit_log.dart`
- `lib/features/signatures/data/models/signature_file.dart`
- `lib/features/signatures/data/repositories/signature_{audit_log,file}_repository_impl.dart`
- `lib/features/signatures/domain/repositories/signature_{audit_log,file}_repository.dart`

Dependencies (existing):
- `crypto` package — likely already in `pubspec.yaml` (grep before adding)
- Platform device ID / GPS service — check `lib/services/` for existing `DeviceInfoService` and `PermissionService`

Reuses:
- `FormResponse.withResponseDataPatch({'signature_audit_id': X})` at `form_response.dart:334`

---

## Concern: Carry forward + guided flow (Spec §3, §5)

**Goal**: First week = blank form; subsequent weeks load prior response + prefill.

Files (NEW):
- `lib/features/forms/domain/usecases/load_prior_1126_use_case.dart`
- `lib/features/forms/domain/usecases/build_carry_forward_1126_use_case.dart`

Repository changes:
- `FormResponseRepository` and implementations: add `getByFormTypeForProject({projectId, formType, descending, limit})` — new query method
- `FormResponseLocalDatasource` — SQL `WHERE form_type = ? AND project_id = ? AND deleted_at IS NULL ORDER BY json_extract(response_data, '$.inspection_date') DESC LIMIT ?`

---

## Concern: Attach to daily entry (Spec §3, §7)

**Goal**: Default to entry matching `inspection_date`, inline create if missing, allow override.

Files (NEW):
- `lib/features/forms/domain/usecases/resolve_1126_attachment_entry_use_case.dart`
- `lib/features/forms/domain/usecases/create_inspection_date_entry_use_case.dart`

Reuses:
- `DailyEntryRepository.getByDate(projectId, date)` at `daily_entry_repository.dart:9`
- `DailyEntryRepository.create(entry)` at `daily_entry_repository.dart:84`

Presentation wiring: the attach picker widget must expose a `TestingKeys.mdot1126AttachDailyEntryPicker` key.

---

## Concern: Export bundling (Spec §3, §10 "Daily export")

**Goal**: IDR + form PDFs + photos in one folder (or zip).

Files (EDIT):
- `lib/features/entries/domain/usecases/export_entry_use_case.dart` — rewrite bundle step; see `patterns/daily-entry-attachment.md`

Plan must decide folder-vs-zip and rename/add the `EntryExport.filePath` semantics accordingly. Tests in `test/features/entries/domain/usecases/export_entry_use_case_test.dart` will need updating.

---

## Concern: Weekly reminder logic (Spec §3 reminder behavior, §5 use case, §7 edge cases)

**Goal**: Anchor date from first signed 1126 + rolling 7-day cycle; not reset by same-week extras; stops when project archived/deleted/inactive; not stored as `todo_items`.

Files (NEW):
- `lib/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart` — see `patterns/use-case.md`

Reuses:
- `ProjectRepository.getById` + `Project.isActive` / `Project.deletedAt`
- `FormResponseRepository.getByFormTypeForProject` (NEW — see Carry-forward concern above)

Presentation bindings:
- Dashboard card: bind in `ProjectDashboardScreen` (`lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`)
- Daily entry banner: bind in the today's entry screen
- Toolbox computed TODO: bind in the toolbox screen — must NOT INSERT into `todo_items`

All three bindings are computed at read time from the use case — there is no new sync surface here.

---

## Concern: UI widgets (Spec §4)

**Goal**: 7 new widgets, all design-system compliant.

Files (NEW, verified paths):
- `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`
- `lib/features/forms/presentation/widgets/rainfall_events_editor.dart`
- `lib/features/forms/presentation/widgets/sesc_measures_checklist.dart`
- `lib/features/forms/presentation/widgets/sesc_measure_add_section.dart`
- `lib/features/forms/presentation/widgets/signature_pad_field.dart`
- `lib/features/forms/presentation/widgets/weekly_sesc_reminder_banner.dart`
- `lib/features/forms/presentation/widgets/weekly_sesc_reminder_card.dart`

Lint constraints: see `ground-truth.md` → "Lint Rules for New Files" — must use `AppButton`, `AppCard`, `AppBanner`, `AppTextField`, `FieldGuideSpacing.of(context)` for all spacing literals, `FieldGuideMotion.of(context)` for durations, etc.

Controller extraction (per CLAUDE.md "Sync-observable controllers"): the form screen must extract a `Mdot1126FormController` (ChangeNotifier) and register it with `WizardActivityTracker` (`lib/features/sync/application/wizard_activity_tracker.dart`) so sync doesn't clobber in-flight drafts.

---

## Concern: Testing keys (Spec §4 TestingKeys list)

**Goal**: 8 new keys available via `TestingKeys.<name>`.

Files (EDIT — see `ground-truth.md` FLAGGED item):
- `lib/shared/testing_keys/testing_keys.dart` — add the 8 keys directly (matches current 0582B convention), OR create `lib/shared/testing_keys/forms_keys.dart` and re-export from `testing_keys.dart` (matches other features).

Plan must pick ONE approach and apply consistently.
