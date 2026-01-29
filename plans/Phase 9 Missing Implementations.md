# Phase 9 Missing Implementations

Created: 2026-01-29
Scope: PR-sized phases to complete missing work identified in Phases 1–9.

Note: This plan focuses on remaining gaps only. It does not restate already completed work.


## Phase A (PR): Template Loading for Imported Forms
Goal: Make imported templates renderable in preview/export using file/bytes sources.

Subphase A1: Template loader in FormPdfService
Steps:
1) Add a template loader that branches on `TemplateSource` (asset/file/bytes).
2) Prefer `templateBytes` if present for file templates; fall back to file path when bytes are absent.
3) Emit clear errors (TemplateLoadException) when file missing and no bytes stored.
4) Add tests for asset vs file/bytes loading.

Target files:
- `lib/features/toolbox/data/services/form_pdf_service.dart`
- `lib/features/toolbox/data/models/inspector_form.dart`
- `test/features/toolbox/services/form_pdf_service_test.dart`


## Phase B (PR): Template Hash + Re-mapping Detection
Goal: Persist template hashes and enforce re-mapping when templates drift.

Subphase B1: Persist template hash on save
Steps:
1) Compute hash from PDF bytes at import/save.
2) Store `template_hash`, `template_field_count`, and `template_bytes` on the form record.
3) Add tests for hash persistence.

Subphase B2: Enforce remap checks
Steps:
1) Use `FieldRegistryService.getRemapStatus` when opening mapping/preview flows.
2) If `templateChanged`, prompt re-map before allowing preview/export.
3) Add a lightweight UI warning when the template hash mismatches.

Target files:
- `lib/features/toolbox/presentation/providers/field_mapping_provider.dart`
- `lib/features/toolbox/presentation/screens/form_import_screen.dart`
- `lib/features/toolbox/presentation/screens/field_mapping_screen.dart`
- `lib/features/toolbox/data/services/field_registry_service.dart`
- `test/features/toolbox/services/template_validation_test.dart`


## Phase C (PR): Persist Auto-fill Provenance Metadata
Goal: Make “clear auto-filled only” durable across sessions.

Subphase C1: Response metadata store
Steps:
1) Add `response_metadata` (JSON) to `form_responses` table.
2) Extend `FormResponse` model with parsed metadata accessor.
3) Save per-field `{source, confidence, is_user_edited}` on update.

Subphase C2: UI integration
Steps:
1) Read metadata on load to rebuild `_autoFillResults` and `_userEditedFields`.
2) Ensure “clear auto-filled only” uses persisted metadata, not just session state.
3) Add tests for metadata round-trip.

Target files:
- `lib/core/database/database_service.dart`
- `lib/features/toolbox/data/models/form_response.dart`
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
- `lib/features/toolbox/data/datasources/local/form_response_local_datasource.dart`
- `test/features/toolbox/data/datasources/form_response_local_datasource_test.dart`


## Phase D (PR): Auto-fill Context Hydration
Goal: Ensure auto-fill reads complete data, not stale provider state.

Subphase D1: Provider hydration or repository reads
Steps:
1) Before auto-fill, explicitly load contractors/locations/entries for the selected project/entry.
2) Alternatively, move context building to repository queries that do not depend on provider state.
3) Add tests for auto-fill data present without prior screen visits.

Target files:
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
- `lib/features/toolbox/data/services/auto_fill_context_builder.dart`
- `lib/features/projects/presentation/providers/project_provider.dart`
- `lib/features/contractors/presentation/providers/contractor_provider.dart`
- `lib/features/locations/presentation/providers/location_provider.dart`
- `lib/features/entries/presentation/providers/daily_entry_provider.dart`


## Phase E (PR): Preview Service Injection + Cache Effectiveness
Goal: Use a single FormPdfService instance so preview caching works as intended.

Subphase E1: DI wiring
Steps:
1) Inject `FormPdfService` into `FormPreviewTab` via Provider.
2) Remove direct instantiation inside preview widget.
3) Add a simple cache-hit test or debug log assertion.

Target files:
- `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`
- `lib/main.dart`
- `test/features/toolbox/services/form_state_hasher_test.dart`

