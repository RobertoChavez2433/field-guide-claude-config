---
feature: forms
type: overview
scope: Inspection form management and PDF generation
updated: 2026-03-30
---

# Forms Feature Overview

## Purpose

The Forms feature manages inspection form templates, form response data entry, and form PDF generation/export. It provides built-in form templates (currently MDOT 0582b), a response CRUD workflow with auto-fill calculations, and PDF filling/export. It is the primary hub for structured inspection data capture beyond free-form diary entries.

## Key Responsibilities

- **Form Template Registry**: Register and surface built-in form configurations via `BuiltinFormConfig` / `BuiltinForms`
- **Form Response CRUD**: Create, read, update, and delete user-filled form responses
- **Auto-Fill Calculations**: Compute derived field values automatically via `AutoFillService`, `OnePointCalculator`, `Mdot0582bCalculator`
- **PDF Filling**: Fill form-specific PDF templates with response data via `FormPdfService` and `fillMdot0582bPdfFields` (top-level function)
- **Form Export**: Package filled PDFs into exportable `FormExport` records
- **Extensible Registries**: `FormScreenRegistry`, `FormPdfFillerRegistry`, `FormValidatorRegistry`, `FormCalculatorRegistry` allow new form types to be added without modifying core logic
- **Two-Phase Initialization**: Registry wiring separated from provider DI via `forms_init.dart`

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/forms/di/forms_providers.dart` | DI wiring — providers, repositories, services |
| `lib/features/forms/di/forms_init.dart` | Registry initialization (two-phase init) |
| `lib/features/forms/data/models/inspector_form.dart` | `InspectorForm` — form template definition |
| `lib/features/forms/data/models/form_response.dart` | `FormResponse` — user's filled response |
| `lib/features/forms/data/models/form_export.dart` | `FormExport` — exported PDF record |
| `lib/features/forms/data/models/auto_fill_result.dart` | `AutoFillResult` — result of an auto-fill calculation |
| `lib/features/forms/data/services/auto_fill_service.dart` | Orchestrates field auto-fill calculations |
| `lib/features/forms/data/services/one_point_calculator.dart` | Single-point compaction calculation logic |
| `lib/features/forms/data/services/form_state_hasher.dart` | Hashes form response state for change detection |
| `lib/features/forms/data/services/mdot_0582b_calculator.dart` | MDOT 0582b field calculation logic |
| `lib/features/forms/data/services/form_pdf_service.dart` | Coordinates PDF filling and export |
| `lib/features/forms/data/registries/builtin_form_config.dart` | Built-in form configuration definitions |
| `lib/features/forms/data/registries/builtin_forms.dart` | Registry of all built-in forms |
| `lib/features/forms/data/registries/form_screen_registry.dart` | Maps form types to their screen widgets |
| `lib/features/forms/data/registries/form_quick_action_registry.dart` | Maps form types to quick action buttons |
| `lib/features/forms/data/registries/form_pdf_filler_registry.dart` | Maps form types to their PDF filler implementations |
| `lib/features/forms/data/registries/form_validator_registry.dart` | Maps form types to their validation logic |
| `lib/features/forms/data/registries/form_calculator_registry.dart` | Maps form types to their field calculators |
| `lib/features/forms/data/registries/form_initial_data_factory.dart` | Generates initial field data for new form responses |
| `lib/features/forms/data/registries/mdot_0582b_form_calculator.dart` | MDOT 0582b calculator registration |
| `lib/features/forms/data/registries/mdot_0582b_registrations.dart` | All MDOT 0582b registry wiring |
| `lib/features/forms/data/validators/mdot_0582b_validator.dart` | MDOT 0582b form validation rules |
| `lib/features/forms/data/pdf/mdot_0582b_pdf_filler.dart` | MDOT 0582b PDF field filling implementation |
| `lib/features/forms/domain/usecases/load_forms_use_case.dart` | Load available form templates |
| `lib/features/forms/domain/usecases/load_form_responses_use_case.dart` | Load saved responses for a form |
| `lib/features/forms/domain/usecases/save_form_response_use_case.dart` | Save (create or update) a form response |
| `lib/features/forms/domain/usecases/delete_form_response_use_case.dart` | Delete a form response |
| `lib/features/forms/domain/usecases/submit_form_response_use_case.dart` | Submit a completed form response |
| `lib/features/forms/domain/usecases/calculate_form_field_use_case.dart` | Trigger auto-fill calculation for a field |
| `lib/features/forms/domain/usecases/export_form_use_case.dart` | Generate and store a form PDF export |
| `lib/features/forms/domain/usecases/manage_documents_use_case.dart` | Manage form-related document attachments |

## Screens (4)

| Screen | Purpose |
|--------|---------|
| `FormsListScreen` | List all available form templates for a project |
| `FormGalleryScreen` | Gallery view of saved form responses |
| `MdotHubScreen` | MDOT 0582b-specific hub with quick actions, proctor data, and status summary |
| `FormViewerScreen` | View or fill a specific form response |

## Providers (3)

| Provider | Responsibility |
|----------|---------------|
| `InspectorFormProvider` | Available form templates, loading state |
| `FormExportProvider` | Export workflow state — generating, saving, and sharing form PDFs |
| `DocumentProvider` | Document attachment management for form responses |

## Widgets

| Widget | Purpose |
|--------|---------|
| `FormAccordion` | Collapsible section container for form field groups |
| `HubHeaderContent` | Header area content for the MDOT hub screen |
| `FormThumbnail` | Thumbnail card for a form response in gallery view |
| `HubQuickTestContent` | Quick test entry area on the hub screen |
| `HubProctorContent` | Proctor reference data display on the hub screen |
| `StatusPillBar` | Row of status pills summarizing form completion state |
| `SummaryTiles` | Tile grid summarizing calculated form field values |

## Integration Points

**Depends on:**
- `entries` — form responses are attachable to diary entries
- `projects` — forms are scoped to a project; project ID is required for CRUD
- `pdf` — PDF filling infrastructure used by `FormPdfService`

**Required by:**
- `entries` — form attachment manager links entries to form responses
- `toolbox` — navigation hub routes to forms list and MDOT hub

## Offline Behavior

Forms are **fully offline-capable**:

- All form templates are built-in (no remote fetch required for templates)
- Form responses are saved to local SQLite immediately
- Auto-fill calculations run entirely on-device
- PDF filling and export run on-device
- Remote datasources sync responses and exports when connectivity is available
