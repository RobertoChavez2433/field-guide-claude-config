# Dependency Graph

## Direct Changes

### New Files
| File | Change Type |
|------|------------|
| `lib/core/database/schema/export_artifact_tables.dart` | NEW — schema for export_artifacts + pay_applications |
| `lib/features/pay_applications/` (entire module) | NEW — data/domain/presentation/di |
| `lib/features/analytics/` (entire module) | NEW — presentation + provider |
| `lib/core/router/routes/pay_app_routes.dart` | NEW — GoRoute registrations |

### Modified Files
| File | Symbol/Line Range | Change Type |
|------|------------------|------------|
| `lib/core/database/database_service.dart:150-240` | `_onCreate` | ADD table creation + triggers |
| `lib/core/database/database_service.dart:239-320` | `_createIndexes` | ADD indexes for new tables |
| `lib/core/database/database_service.dart:326+` | `_onUpgrade` | ADD migration v51->v52 |
| `lib/core/database/schema/schema.dart` | barrel | ADD export for new schema file |
| `lib/core/database/schema/sync_engine_tables.dart:133` | `triggeredTables` | ADD 'export_artifacts', 'pay_applications' |
| `lib/core/database/schema/sync_engine_tables.dart:164` | `tablesWithDirectProjectId` | ADD 'export_artifacts', 'pay_applications' |
| `lib/core/database/schema_verifier.dart:315` | `_columnTypes` | ADD entries for new tables |
| `lib/core/router/app_router.dart:152+` | route spreads | ADD `...payAppRoutes()` |
| `lib/core/di/app_dependencies.dart` | `AppDependencies` | ADD `PayAppDeps` container |
| `lib/core/di/app_providers.dart:40+` | `buildAppProviders` | ADD pay_app providers in Tier 4 |
| `lib/features/sync/adapters/simple_adapters.dart` | `simpleAdapters` | ADD 2 AdapterConfigs |
| `lib/features/sync/engine/sync_registry.dart:31` | `registerSyncAdapters` | ADD 2 adapters in FK order |
| `lib/shared/testing_keys/testing_keys.dart` | `TestingKeys` | ADD 11 new keys |
| `lib/features/quantities/presentation/providers/entry_quantity_provider.dart` | class | ADD `getQuantitiesByDateRange` |
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:320` | `_buildQuickStats` | ADD 4th analytics card |
| `test/core/database/schema_verifier_test.dart` | test | ADD assertions for new tables |
| `test/core/database/database_service_test.dart` | test | ADD migration + table creation tests |

## Upstream Dependencies (what new code depends on)

```
pay_applications feature
  ├── lib/core/database/database_service.dart (table creation)
  ├── lib/shared/datasources/project_scoped_datasource.dart (base datasource)
  ├── lib/shared/datasources/base_remote_datasource.dart (sync remote)
  ├── lib/shared/repositories/base_repository.dart (repository interface)
  ├── lib/shared/providers/safe_action_mixin.dart (provider mixin)
  ├── lib/features/quantities/domain/repositories/bid_item_repository.dart (query bid items)
  ├── lib/features/quantities/domain/repositories/entry_quantity_repository.dart (query quantities)
  ├── lib/features/quantities/data/models/bid_item.dart (data model)
  ├── lib/features/quantities/data/models/entry_quantity.dart (data model)
  ├── lib/features/entries/data/models/daily_entry.dart (date ranges)
  ├── lib/features/auth/presentation/providers/auth_provider.dart (canEditFieldData)
  ├── lib/core/config/app_terminology.dart (bidItem/payItem labels)
  ├── lib/core/logging/logger.dart (structured logging)
  └── lib/features/sync/adapters/adapter_config.dart (sync registration)
```

## Downstream Dependents (what existing code uses changed APIs)

```
EntryQuantityProvider (modified: new getQuantitiesByDateRange method)
  ├── lib/features/dashboard/presentation/screens/project_dashboard_screen.dart
  ├── lib/features/quantities/di/quantities_providers.dart
  └── test/features/quantities/presentation/providers/entry_quantity_provider_extra_test.dart
```

## Data Flow Diagram

```
Pay App Export Flow:
  QuantitiesScreen -> PayApplicationProvider
    -> validateRange() -> PayApplicationRepository (local SQLite query)
    -> getSuggestedNextNumber() -> PayApplicationRepository
    -> exportPayApp()
      -> EntryQuantityRepository.getByDateRange(projectId, start, end)
      -> BidItemRepository.getByProjectId(projectId)
      -> PayAppExcelExporter.generate(bidItems, quantities, previousPayApp)
      -> ExportArtifactRepository.save(artifact)
      -> PayApplicationRepository.save(payApp)

Contractor Comparison Flow:
  PayApplicationDetailScreen -> ContractorComparisonProvider
    -> importContractorArtifact() -> file parser (xlsx/csv/pdf)
    -> matchItems() -> item number first, description fallback
    -> applyManualMatchEdits() -> user cleanup
    -> exportDiscrepancyPdf() -> ExportArtifactRepository.save()

Analytics Flow:
  ProjectDashboardScreen (4th card) -> ProjectAnalyticsScreen
    -> ProjectAnalyticsProvider
      -> BidItemRepository.getByProjectId()
      -> EntryQuantityRepository.getTotalUsedByProject()
      -> PayApplicationRepository.getForProject()
      -> compute changeSinceLastPayApp
```
