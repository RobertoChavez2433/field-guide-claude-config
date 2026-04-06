# Ground Truth

## Schema

| Literal | Source File | Line | Status |
|---------|-----------|------|--------|
| Schema version `51` (current) | `database_service.dart` | 69 | FLAGGED |
| Schema version `50` (CLAUDE.md says) | `.claude/CLAUDE.md` | - | FLAGGED — actual is 51, spec says 50->51+ but 51 is taken. New tables need v52. |
| `entry_exports` table | `schema/entry_export_tables.dart` | 4 | VERIFIED |
| `form_exports` table | `schema/form_export_tables.dart` | 4 | VERIFIED |
| `bid_items` table | `schema/quantity_tables.dart` | 7 | VERIFIED |
| `entry_quantities` table | `schema/quantity_tables.dart` | 27 | VERIFIED |
| `projects` table | `schema/core_tables.dart` | 7 | VERIFIED |
| `daily_entries` table | `schema/entry_tables.dart` | - | VERIFIED |

## Column Names (existing tables referenced by spec)

| Table.Column | Source | Status |
|-------------|--------|--------|
| `bid_items.id` | `bid_item.dart:4` | VERIFIED |
| `bid_items.project_id` | `bid_item.dart:5` | VERIFIED |
| `bid_items.item_number` | `bid_item.dart:6` | VERIFIED |
| `bid_items.description` | `bid_item.dart:7` | VERIFIED |
| `bid_items.unit` | `bid_item.dart:8` | VERIFIED |
| `bid_items.bid_quantity` | `bid_item.dart:9` | VERIFIED |
| `bid_items.unit_price` | `bid_item.dart:10` | VERIFIED |
| `bid_items.bid_amount` | `bid_item.dart:13` | VERIFIED |
| `entry_quantities.entry_id` | `entry_quantity.dart:4` | VERIFIED |
| `entry_quantities.bid_item_id` | `entry_quantity.dart:5` | VERIFIED |
| `entry_quantities.quantity` | `entry_quantity.dart:6` | VERIFIED |
| `entry_quantities.project_id` | `entry_quantity.dart:8` | VERIFIED |
| `entry_exports.file_path` | `entry_export.dart:7` | VERIFIED |
| `entry_exports.remote_path` | `entry_export.dart:8` | VERIFIED |
| `entry_exports.filename` | `entry_export.dart:9` | VERIFIED |
| `form_exports.form_type` | `form_export.dart:14` | VERIFIED |
| `form_exports.file_path` | `form_export.dart:11` | VERIFIED |

## Route Paths

| Route | Source | Status |
|-------|--------|--------|
| `/` (dashboard) | `app_router.dart:123` | VERIFIED |
| `/calendar` | `app_router.dart:131` | VERIFIED |
| `/projects` | `app_router.dart:137` | VERIFIED |
| `/settings` | `app_router.dart:143` | VERIFIED |
| Route spreads: `entryRoutes()`, `formRoutes()`, `projectRoutes()`, `toolboxRoutes()`, `syncRoutes()` | `app_router.dart:152-157` | VERIFIED |

## Provider/Service APIs

| Symbol | File:Line | Signature | Status |
|--------|-----------|-----------|--------|
| `canEditFieldData` | `auth_provider.dart:216` | `bool get canEditFieldData` | VERIFIED |
| `AppTerminology.bidItem` | `app_terminology.dart:23` | `static String get bidItem` | VERIFIED |
| `AppTerminology.useMdotTerms` | `app_terminology.dart:11` | `static bool useMdotTerms` | VERIFIED |
| `EntryQuantityRepository.getTotalUsedByProject` | `entry_quantity_repository.dart:9` | `Future<Map<String, double>> getTotalUsedByProject(String projectId)` | VERIFIED |
| `EntryQuantityRepository.getByEntryId` | `entry_quantity_repository.dart:6` | `Future<List<EntryQuantity>> getByEntryId(String entryId)` | VERIFIED |
| `BidItemRepository.getByItemNumber` | `bid_item_repository.dart:6` | `Future<BidItem?> getByItemNumber(String projectId, String itemNumber)` | VERIFIED |

## Sync Registration

| Literal | Source | Status |
|---------|--------|--------|
| `triggeredTables` list (22 entries) | `sync_engine_tables.dart:133` | VERIFIED |
| `tablesWithDirectProjectId` (14 entries) | `sync_engine_tables.dart:164` | VERIFIED |
| `simpleAdapters` list (13 entries) | `simple_adapters.dart:18` | VERIFIED |
| `registerSyncAdapters` order (22 adapters) | `sync_registry.dart:31` | VERIFIED |
| `ScopeType.viaProject` | `scope_type.dart` | VERIFIED |

## DI Registration

| Literal | Source | Status |
|---------|--------|--------|
| `buildAppProviders` Tier 4 order | `app_providers.dart:70` | VERIFIED |
| `AppDependencies` containers | `app_dependencies.dart:182` | VERIFIED |
| Feature initializer pattern | `form_initializer.dart`, `entry_initializer.dart` | VERIFIED |

## Lint Rules for New Files

No path-trigger lint rules found in `fg_lint_packages/`. The custom lints use AST-level analysis (class structure, import patterns, sync invariants) rather than file-path triggers. New feature files under `lib/features/pay_applications/` and `lib/features/analytics/` will be subject to:
- Architecture rules (23): feature-first layers, provider-only state, no raw SQL in presentation
- Data safety rules (11): soft-delete patterns, toMap includes project_id
- Sync integrity rules (10): change_log trigger-only, no sync_status column
- Test quality rules (8): test naming, mock patterns
