# Data, Database, And Sync Audit

Date: 2026-03-30
Layer: schema, datasources, repositories, sync engine, background sync, DB/Supabase access

## Findings

### 1. High | Confirmed
The codebase still depends heavily on global Supabase singletons even after the DI and domain-layer refactors.

Evidence:

- There are `19` direct `Supabase.instance.client` usages in `lib/`.
- Representative files:
  - `lib/shared/datasources/base_remote_datasource.dart:11`
  - `lib/features/sync/application/sync_orchestrator.dart:224,378`
  - `lib/features/sync/application/background_sync_handler.dart:49,151`
  - `lib/core/di/app_initializer.dart:468,527,548,588,597,642,679`
  - `lib/features/auth/di/auth_providers.dart:57`

Why this matters:

- Remote behavior is still partially global instead of injected.
- Test isolation is weaker than the file layout suggests.
- Sync/auth/data behavior still depends on ambient runtime state.

### 2. High | Confirmed
Direct `DatabaseService()` lookups still bypass the DI graph in production code.

Evidence:

- There are `6` direct `DatabaseService()` usages in `lib/`.
- Non-startup examples:
  - `lib/features/pdf/services/pdf_import_service.dart:193`
  - `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart:86`
  - `lib/features/sync/application/background_sync_handler.dart:30`

Why this matters:

- Local data access is not fully composition-root owned.
- It hides data dependencies inside services/datasources.
- It increases the risk of inconsistent lifetime assumptions around the SQLite singleton.

### 3. High | Confirmed
The database schema still bakes in `mdot_0582b` as the default form type, which conflicts with the recent multi-form infrastructure direction.

Evidence:

- `lib/core/database/schema_verifier.dart:286` still verifies `form_type` as `TEXT NOT NULL DEFAULT 'mdot_0582b'`.
- `lib/core/database/database_service.dart:799` hardcodes the same default.
- `lib/core/database/database_service.dart:812` still coalesces missing values to `'mdot_0582b'`.

Why this matters:

- Form generalization is not neutral at the schema/migration layer.
- New form types remain second-class because fallback behavior still collapses toward 0582B.

Classification: stale architectural specialization surviving the March 28 forms work.

### 4. Medium | Confirmed
`UserProfileSyncDatasource` breaks its own abstraction boundary for user certifications.

Evidence:

- `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart:78-95`
- The datasource directly opens `DatabaseService().database` and writes raw rows into `user_certifications` instead of delegating to a local datasource/repository.

Why this matters:

- Company profile sync and certification sync do not use the same local abstraction story.
- This makes offline profile/certification behavior harder to test and evolve consistently.

### 5. Medium | Confirmed
Background sync duplicates foreground sync bootstrap logic instead of reusing an injected orchestration path.

Evidence:

- `lib/features/sync/application/background_sync_handler.dart:27-68` manually initializes DB, Supabase, registers adapters, and creates a `SyncEngine`.
- `lib/features/sync/application/background_sync_handler.dart:131-167` repeats similar logic again for desktop timer sync.
- `lib/features/sync/application/sync_orchestrator.dart` already owns foreground sync orchestration separately.

Why this matters:

- Foreground and background sync paths can drift behaviorally.
- Fixes to auth/session/context gating have to be duplicated in multiple places.

Classification: recent unfinished integration, not yet normalized after the sync rewrite.

### 6. High | Confirmed
The shared remote-datasource abstraction still hardcodes the Supabase singleton at the base class itself.

Evidence:

- `lib/shared/datasources/base_remote_datasource.dart:9-12` defines `SupabaseClient get supabase => Supabase.instance.client;`

Why this matters:

- This is not just a few leftover call sites; the abstraction root itself still bakes in ambient global state.
- Any datasource inheriting from this base automatically opts out of true client injection and isolated testing.
- It undermines the architectural direction implied by the recent DI refactor.

### 7. Medium | Confirmed
Sync reconciliation logic still performs direct SQLite queries and updates from the DI module instead of flowing through a narrower repository/use-case boundary.

Evidence:

- `lib/features/sync/di/sync_providers.dart:91-179` performs assignment reconciliation with direct queries against `project_assignments` and direct writes into `synced_projects`.
- `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart:86-93` directly inserts pulled `user_certifications` rows into SQLite.

Why this matters:

- Sync correctness is split across orchestrator, DI bootstrap, and ad hoc local SQL.
- That makes sync behavior harder to test, reason about, and change safely after the refactor.
- The recent layering work changed file locations faster than it consolidated the actual data boundary.

### 8. High | Confirmed
`SchemaVerifier` only detects missing columns. It does not verify or repair column definition drift such as wrong defaults, nullability, or type changes.

Evidence:

- `lib/core/database/schema_verifier.dart:330-374` only:
  - checks table existence
  - reads `PRAGMA table_info`
  - compares column names
  - runs `ALTER TABLE ... ADD COLUMN` for missing names
- `lib/core/database/database_service.dart:67-68,87-88` runs `SchemaVerifier.verify(db)` after every production and in-memory open.
- `lib/core/database/schema_verifier.dart:285-288` still declares concrete expected defaults for `form_responses`, including `form_type`, but the verifier never compares those definitions once the column already exists.

Why this matters:

- The post-open "self-healing" safety net is narrower than the surrounding runtime model implies.
- Schema drift can survive silently when the column exists but the definition is wrong.
- That is especially relevant here because the form infrastructure is already carrying specialization drift at the schema-default level.

Classification: stale migration safety net with materially incomplete verification.

### 9. Medium | Confirmed
`SyncOrchestrator` still relies on post-construction setter wiring for critical sync collaborators and auth context, so correct behavior depends on `SyncProviders.initialize()` executing a fragile multi-step setup sequence.

Evidence:

- `lib/features/sync/application/sync_orchestrator.dart:49-59` documents `_userProfileSyncDatasource`, `_syncContextProvider`, and `_appConfigProvider` as dependencies "set after construction."
- `lib/features/sync/application/sync_orchestrator.dart:103-135` shows the constructor only takes `DatabaseService`, while the rest of the sync context arrives later through setters.
- `lib/features/sync/di/sync_providers.dart:50-86` constructs the orchestrator, awaits `initialize()`, then separately injects:
  - `setUserProfileSyncDatasource(...)`
  - `setAdapterCompanyContext(...)`
  - `setSyncContextProvider(...)`
- `lib/features/sync/application/sync_orchestrator.dart:223-229,283-299` shows those late-bound dependencies are used in real sync and post-sync flows.
- `git status --short` currently shows both `lib/features/sync/application/sync_orchestrator.dart` and `lib/features/sync/di/sync_providers.dart` as modified in the working tree.

Why this matters:

- The orchestrator is valid only after a specific boot order has happened elsewhere.
- Alternate entrypoints, tests, or future refactors can instantiate a partially wired orchestrator without any compile-time signal.
- The DI refactor improved file structure, but constructor-level dependency ownership is still unfinished in this layer.

Classification: recent unfinished integration, not dead code.

### 10. Medium | Confirmed
`UserProfileSyncDatasource.updateLastSyncedAt` exposes a parameterized user-targeting API, but the implementation ignores the `userId` argument and relies entirely on ambient authenticated session state.

Evidence:

- `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart:23-29`
- The method signature accepts `String userId`, but the body only calls `rpc('update_last_synced_at')`.
- `lib/features/sync/application/sync_orchestrator.dart:291-294` passes an explicit `userId` after sync success, which suggests the caller believes the method is scoped by that argument.

Why this matters:

- The API contract is misleading: callers appear to control which user is updated, but the implementation does not use the provided value.
- That makes the auth/data boundary harder to reason about in tests, background flows, and future multi-user-safe refactors.
- It is small hygiene debt, but it sits on an auth-sensitive sync path.

Classification: contract drift introduced during recent sync/profile integration.

### 11. Medium | Confirmed
Schema evolution is split across two overlapping repair mechanisms: versioned migration code in `DatabaseService` and post-open repair in `SchemaVerifier`.

Evidence:

- `lib/core/database/database_service.dart:264-277` defines `_addColumnIfNotExists(...)`.
- There are `81` `_addColumnIfNotExists(...)` call sites in `lib/core/database/database_service.dart`.
- `lib/core/database/database_service.dart:67-68,87-88` still runs `SchemaVerifier.verify(db)` after database open.
- `lib/core/database/schema_verifier.dart:330-374` performs a second pass that also adds missing columns independently of migration version gates.

Why this matters:

- There is no single authoritative place to reason about schema guarantees.
- Missed migrations can be masked by runtime repair, but only partially and with different semantics.
- Pre-production debugging gets harder because it is not obvious whether a schema invariant comes from a migration, a startup repair, or both.

Classification: stale migration architecture that survived the recent refactors.

## Coverage Gaps

- No direct test files exist for:
  - `base_remote_datasource`
  - `user_profile_sync_datasource`
  - `background_sync_handler`
- No direct test file exists for `core/database/schema_verifier.dart`, even though it is responsible for runtime repair of schema drift.
- The sync engine is heavily tested, but the bootstrap paths around it are not.
- Existing sync-related tests mostly bypass the concrete production bootstrap path:
  - `lib/test_harness/harness_providers.dart:144` uses `SyncOrchestrator.forTesting(...)`
  - `test/features/sync/presentation/providers/sync_provider_test.dart:12-16` subclasses `SyncOrchestrator.forTesting(...)`
  - `test/features/sync/engine/sync_engine_test.dart:1104-1115` explicitly states parts of the retry coverage "do NOT exercise production code"
  - `test/core/driver/driver_server_sync_status_test.dart:17-21` uses a fake contract surface because the real orchestrator depends on DB/Supabase
- There is still no direct test proving the real `SyncOrchestrator` constructor + setter wiring + global client access path behaves correctly in production shape.
