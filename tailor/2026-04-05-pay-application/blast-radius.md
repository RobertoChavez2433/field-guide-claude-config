# Blast Radius

## FormExport (existing — convergence target for unified export history)

| Metric | Value |
|--------|-------|
| Direct dependents | 10 |
| Total importers | 16 |
| Risk score | 0.86 |

**Confirmed references:**
- `form_export_local_datasource.dart` (7 refs)
- `form_export_remote_datasource.dart` (4 refs)
- `form_export_repository.dart` (impl: 9 refs, interface: 11 refs)
- `export_form_use_case.dart` (4 refs)
- `form_export_provider.dart` (2 refs)
- 5 test files

**Impact**: FormExport is the closest existing analog to the new ExportArtifact model. The spec envisions eventual convergence where form_exports become child records of export_artifacts. For v1, the new export_artifacts table is additive — FormExport is NOT modified.

## EntryExport (existing — convergence target)

| Metric | Value |
|--------|-------|
| Direct dependents | 11 |
| Total importers | 17 |
| Risk score | 0.86 |

**Confirmed references:**
- `entry_export_local_datasource.dart` (6 refs)
- `entry_export_remote_datasource.dart` (4 refs)
- `entry_export_repository.dart` (impl: 8 refs, interface: 9 refs)
- `export_entry_use_case.dart` (3 refs)
- `entry_export_provider.dart` (3 refs)
- `entry_pdf_export_use_case.dart` (1 ref)
- 4 test files

**Impact**: Same as FormExport — additive for v1, eventual convergence target.

## EntryQuantityProvider (modified — new getQuantitiesByDateRange)

| Metric | Value |
|--------|-------|
| Direct importers | 3 |

**Importers:**
- `project_dashboard_screen.dart` (Consumer2 uses it)
- `quantities_providers.dart` (DI registration)
- `entry_quantity_provider_extra_test.dart` (test)

**Impact**: Low risk. Adding a new method doesn't break existing callers.

## Dashboard Screen (modified — 4th quick card)

| Metric | Value |
|--------|-------|
| Direct importers | 0 (leaf screen, registered via router) |

**Impact**: Minimal. Adding a 4th card only affects layout of the dashboard.

## Sync Registry (modified — 2 new adapters)

| Metric | Value |
|--------|-------|
| Direct importers | 3 (`main.dart`, `main_driver.dart`, `sync_engine_factory.dart`) |

**Impact**: Medium. Adapter order is load-bearing. New adapters must be inserted at correct FK position: `export_artifacts` before `pay_applications`, both after `projects`.

## Dead Code Targets

Dead code analysis returned 162K chars of results. Not directly relevant to this spec — no dead code cleanup is in scope. The spec creates new modules rather than modifying dead code.
