---
feature: forms
type: architecture
updated: 2026-03-30
---

# Forms Feature Architecture

## Directory Structure

```
lib/features/forms/
├── forms.dart                              # Feature barrel export
├── di/
│   ├── forms_providers.dart               # DI wiring — providers, repos, services
│   └── form_initializer.dart              # Registry initialization (two-phase init)
├── data/
│   ├── data.dart
│   ├── models/
│   │   ├── models.dart
│   │   ├── inspector_form.dart            # Form template definition
│   │   ├── form_response.dart             # User's filled response
│   │   ├── form_export.dart               # Exported PDF record
│   │   └── auto_fill_result.dart          # Result of an auto-fill calculation
│   ├── datasources/
│   │   ├── datasources.dart
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   ├── inspector_form_local_datasource.dart
│   │   │   ├── form_response_local_datasource.dart
│   │   │   └── form_export_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       ├── inspector_form_remote_datasource.dart
│   │       ├── form_response_remote_datasource.dart
│   │       └── form_export_remote_datasource.dart
│   ├── repositories/
│   │   ├── repositories.dart
│   │   ├── inspector_form_repository.dart
│   │   ├── form_response_repository.dart
│   │   └── form_export_repository.dart
│   ├── services/
│   │   ├── services.dart
│   │   ├── auto_fill_service.dart         # Orchestrates field auto-fill
│   │   ├── one_point_calculator.dart      # Single-point compaction calculations
│   │   ├── form_state_hasher.dart         # Change detection via response hashing
│   │   ├── mdot_0582b_calculator.dart     # MDOT 0582b field calculation logic
│   │   └── form_pdf_service.dart          # PDF filling and export coordination
│   ├── registries/
│   │   ├── form_registries.dart
│   │   ├── builtin_form_config.dart       # Built-in form configuration definitions
│   │   ├── builtin_forms.dart             # Registry of all built-in forms
│   │   ├── form_screen_registry.dart      # Form type → screen widget mapping
│   │   ├── form_quick_action_registry.dart# Form type → quick action mapping
│   │   ├── form_pdf_filler_registry.dart  # Form type → PDF filler mapping
│   │   ├── form_validator_registry.dart   # Form type → validator mapping
│   │   ├── form_calculator_registry.dart  # Form type → calculator mapping
│   │   ├── form_initial_data_factory.dart # Initial field data generation
│   │   ├── mdot_0582b_form_calculator.dart# MDOT 0582b calculator registration
│   │   └── mdot_0582b_registrations.dart  # All MDOT 0582b registry wiring
│   ├── validators/
│   │   └── mdot_0582b_validator.dart      # MDOT 0582b validation rules
│   └── pdf/
│       └── mdot_0582b_pdf_filler.dart     # MDOT 0582b PDF field filling
├── domain/
│   ├── domain.dart
│   ├── repositories/
│   │   ├── repositories.dart
│   │   ├── inspector_form_repository.dart # Interface
│   │   ├── form_response_repository.dart  # Interface
│   │   └── form_export_repository.dart    # Interface
│   └── usecases/
│       ├── usecases.dart
│       ├── load_forms_use_case.dart
│       ├── load_form_responses_use_case.dart
│       ├── save_form_response_use_case.dart
│       ├── delete_form_response_use_case.dart
│       ├── submit_form_response_use_case.dart
│       ├── calculate_form_field_use_case.dart
│       ├── export_form_use_case.dart
│       └── manage_documents_use_case.dart
└── presentation/
    ├── presentation.dart
    ├── providers/
    │   ├── providers.dart
    │   ├── inspector_form_provider.dart
    │   ├── form_export_provider.dart
    │   └── document_provider.dart
    ├── screens/
    │   ├── screens.dart
    │   ├── forms_list_screen.dart
    │   ├── form_gallery_screen.dart
    │   ├── mdot_hub_screen.dart
    │   └── form_viewer_screen.dart
    ├── utils/
    │   ├── utils.dart
    │   └── field_icon_utils.dart
    └── widgets/
        ├── widgets.dart
        ├── form_accordion.dart
        ├── hub_header_content.dart
        ├── form_thumbnail.dart
        ├── hub_quick_test_content.dart
        ├── hub_proctor_content.dart
        ├── status_pill_bar.dart
        └── summary_tiles.dart
```

## Data Layer

### Models

| Model | Purpose |
|-------|---------|
| `InspectorForm` | Form template definition — id, name, fields schema, form type key |
| `FormResponse` | User's filled response — field values map, status, timestamps, project association |
| `FormExport` | Exported PDF record — file path, generated timestamp, linked response |
| `AutoFillResult` | Result of an auto-fill calculation — computed field values and any errors |

### Local Datasources (3)

| Class | Responsibility |
|-------|---------------|
| `InspectorFormLocalDatasource` | SQLite CRUD for form template records |
| `FormResponseLocalDatasource` | SQLite CRUD for form response records |
| `FormExportLocalDatasource` | SQLite CRUD for form export records |

### Remote Datasources (3)

| Class | Responsibility |
|-------|---------------|
| `InspectorFormRemoteDatasource` | Supabase reads/writes for form templates |
| `FormResponseRemoteDatasource` | Supabase reads/writes for form responses |
| `FormExportRemoteDatasource` | Supabase reads/writes for form exports |

### Repository Implementations (3)

| Class | Responsibility |
|-------|---------------|
| `InspectorFormRepositoryImpl` | Coordinates local + remote datasources for form templates |
| `FormResponseRepositoryImpl` | Coordinates local + remote datasources for form responses |
| `FormExportRepositoryImpl` | Coordinates local + remote datasources for form exports |

### Services

| Class | Responsibility |
|-------|---------------|
| `AutoFillService` | Dispatches field auto-fill calculations to the appropriate calculator via `FormCalculatorRegistry` |
| `OnePointCalculator` | Performs single-point Proctor compaction calculations |
| `FormStateHasher` | Hashes form response field state to detect unsaved changes |
| `Mdot0582bCalculator` | MDOT 0582b-specific field calculation logic (density, moisture, percent compaction) |
| `FormPdfService` | Coordinates PDF template filling via `FormPdfFillerRegistry` and delegates to the `pdf` feature |

### Registries

| Class | Responsibility |
|-------|---------------|
| `BuiltinFormConfig` | Static configuration objects for each built-in form type |
| `BuiltinForms` | Aggregates all built-in form configurations into a single registry |
| `FormScreenRegistry` | Maps form type keys to their corresponding screen widget builders |
| `FormQuickActionRegistry` | Maps form type keys to quick action button definitions |
| `FormPdfFillerRegistry` | Maps form type keys to their `FormPdfFiller` implementations |
| `FormValidatorRegistry` | Maps form type keys to their validation functions |
| `FormCalculatorRegistry` | Maps form type keys to their `FormCalculator` implementations |
| `FormInitialDataFactory` | Generates the initial empty field data map for a new form response |
| `Mdot0582bFormCalculator` | Registers the MDOT 0582b calculator with `FormCalculatorRegistry` |
| `Mdot0582bRegistrations` | Wires all MDOT 0582b entries into every registry (screen, pdf, validator, calculator) |

### Validators

| Class | Responsibility |
|-------|---------------|
| `Mdot0582bValidator` | Validates MDOT 0582b form field values and completeness rules |

### PDF Fillers

| Class | Responsibility |
|-------|---------------|
| `Mdot0582bPdfFiller` | Maps MDOT 0582b `FormResponse` field values onto the PDF template |

## Domain Layer

### Repository Interfaces (3)

| Interface | Responsibility |
|-----------|---------------|
| `InspectorFormRepository` | Read/write form templates (local + remote) |
| `FormResponseRepository` | CRUD for form responses (local + remote) |
| `FormExportRepository` | CRUD for form export records (local + remote) |

### Use Cases (8)

| Class | Responsibility |
|-------|---------------|
| `LoadFormsUseCase` | Load all available form templates for the current project |
| `LoadFormResponsesUseCase` | Load saved responses for a given form template |
| `SaveFormResponseUseCase` | Create or update a form response (auto-saves on field change) |
| `DeleteFormResponseUseCase` | Delete a form response and its associated exports |
| `SubmitFormResponseUseCase` | Mark a form response as submitted and lock further edits |
| `CalculateFormFieldUseCase` | Trigger auto-fill calculation for one or more fields via `AutoFillService` |
| `ExportFormUseCase` | Generate a filled PDF and create a `FormExport` record |
| `ManageDocumentsUseCase` | Attach, detach, and list document files linked to a form response |

## Presentation Layer

### Providers (3)

| Class | Type | Responsibility |
|-------|------|---------------|
| `InspectorFormProvider` | `ChangeNotifier` | Available form templates, selected form state, loading/error state |
| `FormExportProvider` | `ChangeNotifier` | PDF export generation, progress state, share/save actions |
| `DocumentProvider` | `ChangeNotifier` | Document attachment list and add/remove operations for a form response |

### Screens (4)

| Screen | Purpose |
|--------|---------|
| `FormsListScreen` | Lists available form templates for the current project |
| `FormGalleryScreen` | Gallery view of all saved responses for a selected form |
| `MdotHubScreen` | MDOT 0582b hub — quick test entry, proctor reference, status summary |
| `FormViewerScreen` | Full form data entry and editing for a single response |

### Widgets (7)

| Widget | Purpose |
|--------|---------|
| `FormAccordion` | Collapsible section container grouping related form fields |
| `HubHeaderContent` | Header area of the MDOT hub (title, summary stats) |
| `FormThumbnail` | Card thumbnail representing a saved form response |
| `HubQuickTestContent` | Inline quick-test data entry panel on the hub |
| `HubProctorContent` | Proctor reference data display panel on the hub |
| `StatusPillBar` | Horizontal row of status pills (e.g., pass/fail per test) |
| `SummaryTiles` | Grid of tiles showing computed summary values (density, moisture, etc.) |

### Utils

| Class | Responsibility |
|-------|---------------|
| `FieldIconUtils` | Maps form field types to their display icons |

## DI Wiring

### `di/forms_providers.dart`

Registers all forms-feature providers, repository implementations, and services into the widget tree:
- `InspectorFormProvider`, `FormExportProvider`, `DocumentProvider`
- `InspectorFormRepositoryImpl`, `FormResponseRepositoryImpl`, `FormExportRepositoryImpl`
- `AutoFillService`, `FormPdfService`, `FormStateHasher`

### `di/form_initializer.dart`

Two-phase initialization — called at app startup before the widget tree is built. Wires all registries by invoking `Mdot0582bRegistrations.register(...)`, which populates `FormScreenRegistry`, `FormPdfFillerRegistry`, `FormValidatorRegistry`, `FormCalculatorRegistry`, and `FormInitialDataFactory` with the MDOT 0582b entries.

## Architectural Patterns

### Registry Pattern

All form-type-specific logic (screens, PDF fillers, validators, calculators) is resolved through a registry keyed on the form type string. Adding a new form type requires only implementing the appropriate interfaces and calling its registration function in `form_initializer.dart` / the registry setup path — no changes to core orchestration code.

Currently MDOT 0582b (`Mdot0582bRegistrations`) is the primary registered form type.

### Calculator Pattern

Field auto-computation follows a delegate pattern: `CalculateFormFieldUseCase` → `AutoFillService` → `FormCalculatorRegistry.lookup(formType)` → `FormCalculator.calculate(fields)` → `AutoFillResult`. Each form type provides its own `FormCalculator` implementation; the service and use case are type-agnostic.

### Two-Phase Initialization

DI is split between `forms_providers.dart` (runtime provider/repository wiring via the widget tree) and `form_initializer.dart` (pre-tree registry population). This ensures registries are populated before any form screen attempts to render, without coupling the registry setup to Flutter's provider lifecycle.

### State Hashing

`FormStateHasher` computes a hash of the current field values map. Providers compare the current hash to the last-saved hash to determine whether there are unsaved changes, enabling dirty-state indicators without tracking every individual field mutation.

## Relationships to Other Features

| Feature | Relationship |
|---------|-------------|
| **Entries** | `ManageDocumentsUseCase` and the form attachment manager link form responses to diary entries |
| **Projects** | All form responses are project-scoped; project ID is required for all CRUD operations |
| **PDF** | `FormPdfService` delegates PDF template loading and filling infrastructure to the `pdf` feature |
| **Toolbox** | Toolbox navigation hub surfaces the forms list and MDOT hub as primary destinations |
| **Sync** | `FormResponse` and `FormExport` records participate in the sync change log like all other syncable entities |
