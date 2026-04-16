# Pattern — Harness Seed Extension

`/driver/seed` is new, but the seeding code already exists. Extend rather than replace.

## Exemplars

- `lib/core/driver/harness_seed_defaults.dart` — string id constants used by both seeders and screen builders.
- `lib/core/driver/harness_seed_data.dart` — `HarnessSeedData` + `seedBaseData(dbService)` + `seedScreenData(dbService, screen, data)` + `_seedFormData(dbService, data)`.
- `lib/core/driver/harness_seed_pay_app_data.dart` — `seedPayAppData(dbService, data)` used by `PayApplicationDetailScreen` / `ContractorComparisonScreen` branches of `seedScreenData`.
- `lib/core/driver/screen_registry.dart:111-285` — screen builders that default missing args from `HarnessSeedData.default*` constants.

## Current signatures

```dart
Future<void> seedBaseData(DatabaseService dbService);                    // idempotent: clear + insert
Future<void> seedScreenData(DatabaseService dbService, String screen, Map<String, dynamic> data);
Future<void> _seedFormData(DatabaseService dbService, Map<String, dynamic> data);
Future<void> seedPayAppData(DatabaseService dbService, Map<String, dynamic> data);
```

`seedBaseData` is idempotent by design — it calls `_clearBaseSeedRows` first (harness_seed_data.dart:156-211), then re-inserts via the feature datasources. Any new precondition must stay idempotent.

## Rules

1. **Always call datasources, never raw SQL inserts.** Existing seeders use `ProjectLocalDatasource`, `LocationLocalDatasource`, `ContractorLocalDatasource`, `PersonnelTypeLocalDatasource`, `DailyEntryLocalDatasource`, `UserProfileLocalDatasource`, `BidItemLocalDatasource`, `FormResponseLocalDatasource`, `InspectorFormLocalDatasource`. Use these.
2. **Cleanup rows go through `db.delete(...)` with explicit `whereArgs`.** Do not call `HardDelete` helpers or hit `change_log` manually (trigger-owned per `rules/backend/data-layer.md`).
3. **Soft delete is the default in production code; harness cleanup is intentional hard delete.** The existing file marks every `db.delete` with a `// harness seed cleanup` comment — preserve that signal.
4. **Add feature-scoped seeders as private functions in the same file or as new files that follow `harness_seed_*_data.dart` naming.** Wire them into the `seedScreenData` switch.
5. **Do not introduce SQLite fixtures from disk.** Precondition data lives inline in Dart so it is test-scoped and type-checked.

## `/driver/seed` body shape (writer decision point)

Option A — screen-shaped (matches existing `seedScreenData`):

```json
POST /driver/seed
{ "screen": "PayApplicationDetailScreen", "data": { "payAppId": "…" } }
```

Option B — precondition-shaped (matches feature spec YAML `requires:`):

```json
POST /driver/seed
{ "preconditions": [
    {"name": "base_data"},
    {"name": "project_draft", "args": {"projectId": "…"}},
    {"name": "location_a", "args": {"projectId": "…"}}
]}
```

Option B aligns with the feature spec YAML more directly and avoids coupling the seed endpoint to screen id strings. Writer picks one; the spec's open question #1 defers the choice.

## What to reuse

- `HarnessSeedData.default*` constants keep default ids stable across builder and seeder.
- `seedBaseData` covers the baseline project/location/contractor/user/bid-item/entry shape used by nearly every sub-flow.
- Feature-specific seeders (`_seedFormData`, `seedPayAppData`) show the pattern: accept `Map<String, dynamic>`, fall back to `HarnessSeedData.default*` for missing keys, call datasource insert/upsert, clear before reseeding.
