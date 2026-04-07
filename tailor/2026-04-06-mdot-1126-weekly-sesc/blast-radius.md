# Blast Radius

## Summary

| Category | Count | Notes |
|---|---|---|
| New files (lib/) | 24 | Forms feature (14) + new signatures feature (8) + schema (1) + asset (1) |
| Edited files (lib/) | 5 | `form_type_constants`, `builtin_forms`, `database_service`, `schema_verifier`, `simple_adapters` |
| Edited files (entries) | 1 | `export_entry_use_case.dart` — one-folder bundling |
| New Supabase migration | 1 | signature tables + RLS + realtime + bucket |
| Test files (new) | ~18 | One per new production file (unit + widget + integration + sync) |
| Test files (edited) | 3 | `schema_verifier_drift_test`, adapter_config_test, characterization tests |

## Per-Symbol Blast Radius

### `DatabaseService._onCreate` / `_onUpgrade`

- **Direct**: version int, create SQL list, trigger list, upgrade block → 1 file
- **Dependents**: every test that bootstraps a full DB via `_createFullSchema()` mirror (2+ test helpers)
- **Tests**: `test/features/projects/integration/project_lifecycle_integration_test.dart:587` and `test/features/sync/engine/scope_revocation_cleaner_test.dart:152` both maintain private `_createFullSchema` copies that will drift if not updated
- **Risk**: If either test helper is not updated, downstream DB-backed tests will fail with missing tables
- **Cleanup target**: Investigate consolidating both `_createFullSchema` helpers into a single shared `lib/core/database/schema.dart`-derived helper (out of scope but worth noting)

### `simpleAdapters` const list

- **Direct**: add 2 entries → 1 file
- **Dependents**: `SyncRegistry.adapterFor()` iterates this; `push_table_planner` orders by `fkDeps`; `adapter_config_test` asserts coverage; `validate_sync_adapter_registry.py` CI script
- **Tests**: `test/features/sync/adapters/adapter_config_test.dart` must get new fixture rows
- **Risk**: File-backed adapters require exact `buildStoragePath` function signatures matching `form_exports` exemplar. EXIF stripping is `false` for signatures (PNG not JPEG).

### `ExportEntryUseCase.call`

- **Direct**: rewrite bundle step → 1 file
- **Dependents**: `EntryExportProvider`, `ExportFormUseCase` (unchanged), `ExportArtifactRepository` (unchanged)
- **Tests**: `test/features/entries/domain/usecases/export_entry_use_case_test.dart` — fully mocked with `_StubFormPdfService`, will need "one-folder" assertions
- **Risk**: One-folder bundling contradicts current single-PDF assumption (`savedFilePath = paths.first`). Must either rewrite to bundle or keep bundle path + folder path both recorded.

### `FormResponse` model

- **Direct**: no model field changes needed — `response_data` JSON is the carrier
- **Dependents**: n/a
- **Tests**: new unit tests for 1126-specific JSON shape

### `builtin_forms.dart`

- **Direct**: append 1 entry → 1 file
- **Dependents**: `registerBuiltinForms()` (auto-iterates); InspectorFormRepository seed
- **Tests**: `test/features/forms/data/registries/seed_builtin_forms_test.dart` fixture uses `_FakeInspectorFormRepository`

## Dead Code / Cleanup Targets

- None identified. 0582B registrations are clean and live; 1126 layers in on top of the same pattern.

## Risk Table

| Risk | Likelihood | Mitigation |
|---|---|---|
| Schema version bump forgotten in one place | HIGH | CLAUDE.md rule: "schema changes touch 5 files". Plan must enumerate explicitly. |
| `_createFullSchema` test helpers drift | MED | Grep for `_createFullSchema` before merging; update in lockstep |
| Design-system lint failures on new widgets | HIGH | Pre-flight: every new presentation file must use AppButton/AppCard/AppBanner from first commit |
| Signature PNG hash mismatch between devices | MED | Use canonical encoding (RGBA, PNG compression level fixed) before SHA-256 |
| Concurrent 1126 on two devices → report_number collision | MED (per spec) | Accept last-write-wins, surface in existing conflict viewer (no new code) |
| Re-entry of ExportEntryUseCase while signature cleared | LOW | `Mdot1126Validator` blocks export when `signature_audit_id == null` |
| `signature_files` storage bucket provisioning | MED | Supabase migration must create bucket + RLS policies; manual verification on staging |
