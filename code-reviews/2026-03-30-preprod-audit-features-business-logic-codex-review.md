# Features And Business Logic Audit

Date: 2026-03-30
Layer: feature behavior, domain logic, form infrastructure, feature completeness

## Findings

### 1. High | Confirmed
Form generalization is still partial. The new registry architecture exists, but 0582B assumptions still leak through active production code.

Evidence:

- `lib/features/forms/data/models/inspector_form.dart:217-218` still exposes `is0582B`.
- `lib/features/forms/presentation/providers/inspector_form_provider.dart:384-396` still hardcodes `'mdot_0582b'` for proctor-row normalization.
- `lib/features/forms/presentation/screens/mdot_hub_screen.dart:719-723` still searches for the builtin form with explicit 0582B heuristics.
- `lib/core/database/schema_verifier.dart:286` and `lib/core/database/database_service.dart:799,812` still default/coalesce form type to 0582B.

Why this matters:

- The form system is structurally generalized but behaviorally still single-form-biased.
- Adding another form type will still collide with hidden 0582B assumptions.

### 2. High | Confirmed
`FormGalleryScreen` does not use registry-backed initial data when creating new forms.

Evidence:

- `lib/features/forms/presentation/screens/form_gallery_screen.dart:147-154`
- New responses are created with `responseData: '{}'` regardless of form type.

Why this matters:

- The code bypasses form-specific initial state factories.
- Any form that expects structured default data will either degrade or require fallback logic elsewhere.

Classification: unfinished recent work from the forms-infrastructure rollout.

### 3. High | Confirmed
`FormPdfService.generateFilledPdf()` builds a synthetic asset path that diverges from the seeded builtin template path.

Evidence:

- `lib/features/forms/data/services/form_pdf_service.dart:1141-1145` builds a stub form with `templatePath: 'assets/forms/$formType.pdf'`.
- Builtin form registration uses `assets/templates/forms/mdot_0582b_form.pdf` in `lib/features/forms/data/registries/builtin_forms.dart`.
- `generateFilledPdf()` is not dead code:
  - `lib/features/forms/domain/usecases/export_form_use_case.dart:30` calls it directly.

Why this matters:

- Export behavior depends on a template path convention that does not match the current builtin registration path.
- This is a brittle export path for the current 0582B form and an obvious hazard for future forms.

### 4. Medium | Confirmed
The deprecated 0582B-only screen is still part of the maintained feature surface.

Evidence:

- `lib/features/forms/presentation/screens/forms_list_screen.dart` still hardcodes 0582B creation, listing, copy, and labels.
- `lib/features/forms/presentation/screens/screens.dart:3` still exports it.
- `lib/test_harness/screen_registry.dart:84` and `lib/test_harness/flow_registry.dart:33,48,210,225` still wire it into harness flows.

Why this matters:

- This is no longer just historical code sitting on disk; it is still part of non-production runtime surfaces and tests.
- It increases maintenance cost and keeps old assumptions alive.

Classification: stale post-refactor drift.

### 5. Medium | Confirmed
The support-ticket feature is operationally incomplete even though the schema and UI landed.

Evidence:

- `lib/features/settings/presentation/providers/support_provider.dart:131-133`
- The provider persists locally, but explicitly defers the sync trigger.

Why this matters:

- The feature looks complete at the UI layer but is still relying on later sync side effects to reach the backend.
- This should be treated as unfinished recent work, not dead code.

### 6. Medium | Confirmed
The supposedly generic `FormResponse` model still carries substantial 0582B-specific structure and legacy compatibility behavior.

Evidence:

- `lib/features/forms/data/models/form_response.dart:210-251` exposes `parsedTestRows` and `parsedProctorRows` as 0582B-specific convenience getters.
- `lib/features/forms/data/models/form_response.dart:298-330` exposes `withTableRow`, `withProctorRows`, and `withTestRows`, again in 0582B-shaped terms.
- `lib/features/forms/data/models/form_response.dart:73-78,138-160,223-229` still preserves deprecated `tableRows` compatibility paths.

Why this matters:

- The model layer is still biased toward one form family even after the registry-based generalization.
- A second real form type would still inherit a domain model whose convenience API is shaped around 0582B semantics.
- The refactor changed naming and registration first, but the core response model remains only partially generalized.

### 7. Medium | Confirmed
`FormViewerScreen` is generic only at the shell level; the substantive body still treats 0582B as the only fully supported form.

Evidence:

- `lib/features/forms/presentation/screens/form_viewer_screen.dart:266-267` titles the screen from `response.formType`, implying generic support.
- `lib/features/forms/presentation/screens/form_viewer_screen.dart:297-306` conditionally renders tests, proctors, and standards only when `response.formType == 'mdot_0582b'`.

Why this matters:

- Non-0582B forms currently fall back to a reduced viewer experience rather than a truly form-driven renderer.
- This is feature incompleteness, not just UI debt, because the runtime behavior differs by hidden form-type assumptions.

## Coverage Gaps

- Form feature tests exist for both `FormGalleryScreen` and `FormsListScreen`, which is useful, but the coexistence itself is part of the drift problem.
- No direct test exists for the `FormPdfService.generateFilledPdf()` asset-path convention against real builtin form registrations.
- No direct test file exists for `InspectorFormProvider`, even though it now concentrates form loading, response creation, save/update flows, and 0582B-specific normalization.
