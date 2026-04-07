# Dependency Graph

## Direct Changes

| File | Change | Kind |
|---|---|---|
| `lib/features/forms/data/registries/form_type_constants.dart` | Add `kFormTypeMdot1126`, `kFormTemplateMdot1126` | EDIT |
| `lib/features/forms/data/registries/builtin_forms.dart` | Append `BuiltinFormConfig` for `mdot_1126` | EDIT |
| `lib/features/forms/data/registries/mdot_1126_registrations.dart` | NEW — single-entry registration (calc? no; validator yes; initial data yes; pdf filler yes; quick action yes) | CREATE |
| `lib/features/forms/data/pdf/mdot_1126_pdf_filler.dart` | NEW — `fillMdot1126PdfFields` pure function | CREATE |
| `lib/features/forms/data/validators/mdot_1126_validator.dart` | NEW — `validateMdot1126` pure function | CREATE |
| `lib/features/forms/domain/usecases/load_prior_1126_use_case.dart` | NEW | CREATE |
| `lib/features/forms/domain/usecases/build_carry_forward_1126_use_case.dart` | NEW | CREATE |
| `lib/features/forms/domain/usecases/sign_form_response_use_case.dart` | NEW | CREATE |
| `lib/features/forms/domain/usecases/invalidate_form_signature_on_edit_use_case.dart` | NEW | CREATE |
| `lib/features/forms/domain/usecases/resolve_1126_attachment_entry_use_case.dart` | NEW | CREATE |
| `lib/features/forms/domain/usecases/create_inspection_date_entry_use_case.dart` | NEW | CREATE |
| `lib/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart` | NEW | CREATE |
| `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart` | NEW | CREATE |
| `lib/features/forms/presentation/widgets/rainfall_events_editor.dart` | NEW | CREATE |
| `lib/features/forms/presentation/widgets/sesc_measures_checklist.dart` | NEW | CREATE |
| `lib/features/forms/presentation/widgets/sesc_measure_add_section.dart` | NEW | CREATE |
| `lib/features/forms/presentation/widgets/signature_pad_field.dart` | NEW | CREATE |
| `lib/features/forms/presentation/widgets/weekly_sesc_reminder_banner.dart` | NEW | CREATE |
| `lib/features/forms/presentation/widgets/weekly_sesc_reminder_card.dart` | NEW | CREATE |
| `lib/features/signatures/` (new feature module) | NEW dir | CREATE |
| `lib/features/signatures/data/models/signature_audit_log.dart` | NEW | CREATE |
| `lib/features/signatures/data/models/signature_file.dart` | NEW | CREATE |
| `lib/features/signatures/data/datasources/local/signature_audit_log_local_datasource.dart` | NEW | CREATE |
| `lib/features/signatures/data/datasources/local/signature_file_local_datasource.dart` | NEW | CREATE |
| `lib/features/signatures/data/repositories/signature_audit_log_repository_impl.dart` | NEW | CREATE |
| `lib/features/signatures/data/repositories/signature_file_repository_impl.dart` | NEW | CREATE |
| `lib/features/signatures/domain/repositories/...` | NEW abstract interfaces | CREATE |
| `lib/core/database/schema/signature_tables.dart` | NEW — `SignatureTables` class with both create/trigger SQL | CREATE |
| `lib/core/database/database_service.dart` | Bump version 53 → **54**, add `_onUpgrade` migration step, wire new table creates + triggers | EDIT |
| `lib/core/database/schema_verifier.dart` | Register expected columns for `signature_audit_log`, `signature_files` | EDIT |
| `lib/features/sync/adapters/simple_adapters.dart` | Add two `AdapterConfig` entries (audit log standard adapter, signature_files file-backed adapter) | EDIT |
| `lib/features/entries/domain/usecases/export_entry_use_case.dart` | Extend to group IDR + form PDFs + photos in one folder + signature file pass-through | EDIT |
| `lib/shared/testing_keys/testing_keys.dart` OR new `forms_keys.dart` | Add 1126 keys | EDIT/CREATE |
| `assets/templates/forms/mdot_1126_form.pdf` | Copy from `.claude/specs/assets/mdot-1126-weekly-sesc.pdf` | CREATE |
| `pubspec.yaml` | Add asset, add `signature` package dep | EDIT |
| `supabase/migrations/20260408000000_signature_tables.sql` | NEW — tables, RLS, Realtime publication, storage bucket | CREATE |

## Upstream (who we depend on)

```
mdot_1126_pdf_filler.dart
  ↳ (pure function — no imports beyond Map<String,dynamic>)

mdot_1126_validator.dart
  ↳ (pure function)

build_carry_forward_1126_use_case.dart
  ↳ FormResponse (parsedResponseData, toMap)
  ↳ LoadPrior1126UseCase

sign_form_response_use_case.dart
  ↳ SignatureAuditLogRepository (NEW)
  ↳ SignatureFileRepository (NEW)
  ↳ FormResponseRepository (existing)
  ↳ crypto (SHA-256)
  ↳ path_provider (app docs dir)

mdot_1126_form_screen.dart
  ↳ InspectorFormProvider (existing)
  ↳ All 1126 use cases
  ↳ Design system: AppButton, AppCard, AppTextField, AppBanner
  ↳ package:signature (canvas)

compute_weekly_sesc_reminder_use_case.dart
  ↳ FormResponseRepository.getResponsesForEntry (cross reference) — actually needs new method `getResponsesForProject(projectId, formType)`
  ↳ ProjectRepository (for archived/deleted/inactive)
  ↳ DailyEntryRepository.getByDate

resolve_1126_attachment_entry_use_case.dart
  ↳ DailyEntryRepository.getByDate
  ↳ CreateInspectionDateEntryUseCase
```

## Downstream (who depends on what we build)

```
registerMdot1126()  ← called by registerBuiltinForms() (exists, called on app init)
Mdot1126FormScreen  ← referenced by FormScreenRegistry (decoupled — no static imports)
ExportEntryUseCase (modified) ← EntryExportProvider
WeeklySescReminderBanner  ← DailyEntryScreen (today's entry) [NEW binding point]
WeeklySescReminderCard    ← ProjectDashboardScreen [NEW binding point]
WeeklySescToolboxTodo     ← ToolboxScreen TODO widget [NEW binding point — computed, not stored]
signature_audit_log adapter ← SyncRegistry (pushed via simple_adapters list)
signature_files adapter     ← SyncRegistry + FileSyncHandler
```

## Data Flow

```
Forms Hub ─────► New 1126 Tap
                     │
                     ▼
            InspectorFormProvider.createResponse(formType='mdot_1126')
                     │
                     ▼
      LoadPrior1126UseCase ── (if found) ──► BuildCarryForward1126UseCase
                     │                             │
                     │                             ▼
                     └─────────► Initial response_data JSON payload
                                    │
                                    ▼
                        Mdot1126FormScreen (guided steps)
                                    │
                     ┌──────────────┼──────────────┐
                     ▼              ▼              ▼
         RainfallEventsEditor  SescMeasures   SignaturePadField
                                 Checklist
                                    │
                                    ▼
                         SignFormResponseUseCase
                          (SHA-256 pre-sign PDF + PNG,
                           write signature_files + signature_audit_log,
                           stamp signature_audit_id into response_data)
                                    │
                                    ▼
                    Resolve1126AttachmentEntryUseCase
                     │                    │
                     ▼                    ▼
              existing entry    CreateInspectionDateEntryUseCase
                     │                    │
                     └──────────┬─────────┘
                                ▼
                  form_response.entry_id = chosen entry.id
                                │
                                ▼
                      save → triggers → change_log
                                │
                                ▼
                          Sync push (bidirectional)
                                │
                                ▼
          On export: ExportEntryUseCase groups IDR + PDFs + photos
```

## Import Chains — Registry Hook

`registerBuiltinForms()` (existing) → iterates `builtinForms` → calls each `BuiltinFormConfig.registerCapabilities()` → our new `registerMdot1126()` → registers into 5 registries.

`FormScreenRegistry` registrations are deferred to UI layer init; confirm where `registerMdot0582BScreen` is currently bound — same place must bind `Mdot1126FormScreen`.
