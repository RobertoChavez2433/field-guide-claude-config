# Forms PRD

## Purpose
Enable inspectors to fill out, manage, and export structured inspection forms (e.g., MDOT 0582B) scoped to a project. Forms provide a typed, validated data-capture layer on top of raw entries, with auto-fill from project data, per-field calculations, and PDF export. The MDOT Hub provides a dedicated landing point for MDOT-specific form workflows.

## Core Capabilities
- Browse available form templates from a gallery of built-in form definitions
- Create, edit, and delete form responses scoped to a project
- Form lifecycle: draft (editable) → submitted (immutable after submit)
- Auto-populate fields from existing project data via AutoFillService
- Per-field and aggregate calculations (e.g., IDR via Mdot0582BCalculator)
- Field validation with form-type-specific rules (e.g., validateMdot0582B)
- PDF export of completed form responses (e.g., fillMdot0582bPdfFields)
- MDOT Hub screen as a dedicated entry point for MDOT form types
- Quick actions per form type (e.g., shortcut to common operations)
- Change detection via FormStateHasher to avoid unnecessary saves

## Registry System
The forms feature uses a registry pattern to decouple form-type logic from shared infrastructure. Each registry maps a form type string to a handler:

- **FormScreenRegistry** — maps form type → screen builder (widget factory)
- **FormPdfFillerRegistry** — maps form type → PDF filler implementation
- **FormCalculatorRegistry** — maps form type → calculator implementation
- **FormValidatorRegistry** — maps form type → validator implementation
- **FormQuickActionRegistry** — maps form type → list of quick action definitions
- **FormInitialDataFactory** — creates initial (empty/defaulted) data map for a new form response of a given type

New form types are registered at startup in `forms_init.dart`; no conditional branching required in shared use cases or screens.

## Data Model
- **`inspector_forms`** (SQLite) — immutable built-in form definitions; seeded at app init
  - Key fields: `id`, `form_type`, `name`, `description`, `version`, `is_active`
- **`form_responses`** (SQLite) — project-scoped, one row per response instance
  - Key fields: `id`, `project_id`, `form_id`, `form_type`, `status` (draft/submitted), `data` (JSON), `created_at`, `updated_at`
  - Status is terminal once set to `submitted`; no further edits permitted
- **FormExport** — in-memory data container assembled at export time (not persisted)
- **AutoFillResult** — in-memory result of an auto-fill operation, carrying applied field values and any skipped fields with reasons

Sync: form_responses rows are captured by `change_log` triggers on insert/update/delete. Sync is driven by the sync engine reading `change_log`; there is no per-row `sync_status` column.

## MDOT 0582B Specifics
The MDOT 0582B Density Test Report (IDR) is the first and primary form type:

- **Mdot0582BCalculator** — computes IDR fields: dry density, percent compaction, moisture correction, and pass/fail determination
- **validateMdot0582B** — top-level function enforcing field-level rules: required fields, numeric range checks, proctor reference validity, and cross-field constraints
- **fillMdot0582bPdfFields** — top-level function that fills the official MDOT PDF template with form response data, handling field mapping and formatting

## Services
- **AutoFillService** — reads project, location, contractor, and entry data to pre-populate matching form fields; returns an `AutoFillResult`
- **OnePointCalculator** — performs single-point proctor calculation used in certain MDOT workflows
- **FormStateHasher** — hashes the current form data map to a string; used by the UI provider to detect unsaved changes and suppress redundant saves
- **FormPdfService** — orchestrates PDF export: selects the correct filler from `FormPdfFillerRegistry`, invokes it, and hands the output to the PDF feature for display or share

## Use Cases
| Use Case | Responsibility |
|---|---|
| `LoadFormsUseCase` | Load all active `InspectorForm` definitions |
| `LoadFormResponsesUseCase` | Load all form responses for a project, optionally filtered by form type |
| `SaveFormResponseUseCase` | Insert or update a draft form response |
| `SubmitFormResponseUseCase` | Transition a form response from draft → submitted (validates first) |
| `DeleteFormResponseUseCase` | Delete a draft form response (submitted responses cannot be deleted) |
| `CalculateFormFieldUseCase` | Invoke the registered calculator for a form type and return updated field values |
| `NormalizeProctorRowUseCase` | Normalize a proctor data row for MDOT 0582B (handled inline in InspectorFormProvider.appendMdot0582bProctorRow()) |
| `ManageDocumentsUseCase` | Manage attached document references for a form response |
| `ExportFormUseCase` | Assemble a `FormExport` and trigger PDF generation via `FormPdfService` |

## Screens
- **FormsListScreen** — lists all form responses for the active project; supports create, open, and delete actions; shows status badges (draft / submitted)
- **FormGalleryScreen** — displays available form templates from `inspector_forms`; tapping a template creates a new response and navigates to the viewer
- **MdotHubScreen** — MDOT-specific landing hub; shows MDOT form types, recent MDOT responses, and MDOT quick actions
- **FormViewerScreen** — renders the editing UI for a specific form response; delegates to the screen builder registered in `FormScreenRegistry` for the form type; enforces read-only mode once submitted

## User Flow
From the project dashboard, the inspector opens the Forms section to see FormsListScreen. To start a new form, they tap the gallery icon to reach FormGalleryScreen and select a template. The FormViewerScreen opens with auto-filled fields (via AutoFillService). The inspector fills in remaining fields; calculations update in real time. On save, SaveFormResponseUseCase persists the draft. When complete, SubmitFormResponseUseCase locks the response. The inspector can then export a PDF via ExportFormUseCase. MDOT workflows can also be accessed directly from MdotHubScreen.

## Offline Behavior
Full read/write offline. All form responses and definitions are stored in SQLite. PDF export is local. Changes to `form_responses` rows are captured by `change_log` triggers and synced to Supabase when connectivity is available via the sync engine. No sync_status column is used.

## DI
- **`forms_providers.dart`** — Provider definitions for all forms repositories, services, and use cases
- **`forms_init.dart`** — startup registration of all form types into the five registries and `FormInitialDataFactory`

## Dependencies
- Features: projects (parent scope), entries (auto-fill source), contractors (auto-fill source), locations (auto-fill source), pdf (PDF export/display), sync (change_log-driven cloud sync)
- Packages: `sqflite`, `provider`, `uuid`, `go_router`, `intl`, `pdfx` or equivalent PDF filler package

## Owner Agent
backend-data-layer-agent (data layer), frontend-flutter-specialist-agent (presentation)
