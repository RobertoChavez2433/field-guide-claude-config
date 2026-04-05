# Construction Inspector App

Cross-platform mobile/desktop app for construction inspectors. Offline-first with cloud sync.

**HARD CONSTRAINT: Security is non-negotiable. No shortcuts that bypass approval flows, weaken RLS, or create privilege escalation paths.**

## App Identity
| Property | Value |
|----------|-------|
| Package name | `construction_inspector` |
| App ID | `com.fieldguideapp.inspector` |
| Version | `0.1.2+3` |
| Dart SDK | `^3.10.7` |
| Flutter (CI-pinned) | `3.38.9` |
| Android | minSdk 31 / targetSdk 36 / compileSdk 36 |
| iOS | deployment target 13.0 |

## Project Structure
```
lib/
├── core/
│   ├── analytics/       # Analytics barrel
│   ├── bootstrap/       # 8-phase app initialization (AppInitializer, CoreServices, etc.)
│   ├── config/          # Supabase, Sentry, test mode, app terminology
│   ├── database/        # SQLite schema (v50, 36 tables) + schema verifier
│   │   └── schema/      # 15 domain schema files + barrel
│   ├── design_system/   # 24 reusable app components (AppScaffold, AppDialog, AppText, etc.)
│   ├── di/              # DI root (AppBootstrap, AppProviders, AppDependencies)
│   ├── driver/          # HTTP test driver infrastructure (8 files)
│   ├── logging/         # Logger + route observer
│   ├── router/          # go_router setup + 7 route files
│   └── theme/           # Theme data, DesignConstants, FieldGuideColors
├── shared/
│   ├── datasources/     # Base local/remote datasource classes
│   ├── domain/          # Shared domain barrel
│   ├── models/          # Shared models (PagedResult)
│   ├── providers/       # Base ChangeNotifier providers (BaseListProvider, PagedListProvider)
│   ├── repositories/    # Base repository class
│   ├── services/        # PreferencesService
│   ├── testing_keys/    # 16 widget test key files organized by feature
│   ├── utils/           # Date, enum, string, math, navigation, snackbar utilities
│   ├── validation/      # Reusable validators
│   └── widgets/         # Shared UI widgets (empty state, permission dialog, etc.)
├── features/            # 17 features (see Feature Inventory below)
└── services/            # Cross-cutting: document, image, permission, photo, soft_delete, startup_cleanup
```

### Feature Inventory
| Feature | Layers |
|---------|--------|
| auth | data, domain, presentation, di, services |
| calculator | data, domain, presentation, di |
| contractors | data, domain, presentation, di |
| dashboard | domain, presentation |
| entries | data, domain, presentation, di |
| forms | data, domain, presentation, di |
| gallery | domain, presentation, di |
| locations | data, domain, presentation, di |
| pdf | data, domain, presentation, di, services |
| photos | data, domain, presentation, di |
| projects | data, domain, presentation, di |
| quantities | data, domain, presentation, di, utils |
| settings | data, domain, presentation, di |
| sync | data, domain, presentation, di, application, engine, adapters, config |
| todos | data, domain, presentation, di |
| toolbox | domain, presentation |
| weather | domain, presentation, di, services |

## Key Files
| File | Purpose |
|------|---------|
| `lib/main.dart` | Production entry point (Sentry, zone-guarded bootstrap) |
| `lib/main_driver.dart` | Test/driver entry point (HTTP driver server) |
| `lib/core/di/app_providers.dart` | All providers composed in tier order (Tier 0-5) |
| `lib/core/bootstrap/app_initializer.dart` | Phased dependency creation and auth listener |
| `lib/core/router/app_router.dart` | go_router routes (shell + full-screen) |
| `lib/core/database/database_service.dart` | SQLite schema v50, 36 tables |
| `lib/core/design_system/` | 24 app-level UI components |
| `lib/features/sync/` | 5-layer sync system (see Sync Architecture) |
| `lib/features/sync/application/sync_coordinator.dart` | Sync entry point (replaces SyncOrchestrator) |
| `lib/features/sync/application/sync_query_service.dart` | Dashboard query surface |
| `lib/features/sync/adapters/simple_adapters.dart` | 13 data-driven adapter configs |

## Data Flow
```
Screen -> Provider -> UseCase -> Repository -> Datasource -> SQLite (local) -> Supabase (sync)
```
- **Providers**: `ChangeNotifier` via `provider` package (~32 providers, sole state management)
- **Repositories**: Abstract interfaces in `domain/repositories/`, implementations in `data/repositories/`
- **Datasources**: `GenericLocalDatasource<T>` (SQLite), `BaseRemoteDatasource<T>` (Supabase)
- **Sync**: SQLite triggers auto-populate `change_log` — no per-row `sync_status` field

## Sync Architecture
```
Presentation: SyncProvider, SyncDashboardScreen, ConflictViewerScreen
Application:  SyncCoordinator, SyncLifecycleManager, SyncRetryPolicy, ConnectivityProbe, SyncTriggerPolicy, PostSyncHooks, SyncQueryService, BackgroundSyncHandler, FcmHandler, RealtimeHintHandler
Engine:       SyncEngine (slim ~214 lines), PushHandler, PullHandler, SupabaseSync, LocalSyncStore, FileSyncHandler, SyncErrorClassifier, EnrollmentHandler, FkRescueHandler, MaintenanceHandler
Unchanged:    ChangeTracker, ConflictResolver, IntegrityChecker, DirtyScopeTracker, OrphanScanner, StorageCleanup, SyncMutex
Adapters:     13 AdapterConfig (data-driven) + 9 complex adapter classes (22 total; declare FK ordering + scope type)
Domain:       SyncResult, SyncStatus, SyncErrorKind, ClassifiedSyncError, SyncDiagnosticsSnapshot, SyncEvent, SyncMode, DirtyScope
```

## Gotchas
- **Soft-delete is the default** — `delete()` = soft-delete. Hard-delete requires explicit `hardDelete()`. All reads auto-filter `deleted_at IS NULL`.
- **change_log is trigger-only** — 20 tables have SQLite triggers gated by `sync_control.pulling='0'`. Never manually INSERT.
- **Provider tiers 1-2 are NOT in widget tree** — Datasources/repos created in AppInitializer via typed `*Deps` containers. Only tiers 0, 0.5, 3-5 are widget-tree providers.
- **Tier 4 ordering is load-bearing** — Forms MUST precede entries (`ExportEntryUseCase` depends on `ExportFormUseCase`).
- **`is_builtin=1` rows are server-seeded** — Triggers skip them, cascade-delete skips them, push skips them.
- **`flusseract`** — Embedded Tesseract OCR FFI plugin at `packages/flusseract/`. Drives Android minSdk 31.
- **AppTerminology dual-mode** — `useMdotTerms` flag switches all UI labels (IDR/DWR, Bid Item/Pay Item).
- **AppDialog uses `actionsBuilder:`** — NOT `actions:`. Pop dialog BEFORE `auth.signOut()` (GoRouter redirect race).
- **PRAGMAs via `rawQuery`** — Android API 36 rejects PRAGMA via `execute()`.
- **Schema changes touch 5 files** — database_service, schema/*.dart, schema_verifier, + 2 test files. See `rules/database/schema-patterns.md`.
- **SyncOrchestrator no longer exists** — use `SyncCoordinator` (replaced in Phase 7 refactor).
- **SyncProvider no longer exposes `get orchestrator`** — use `SyncQueryService` for dashboard data.
- **Error classification is in SyncErrorClassifier only** — no Postgres code matching elsewhere.

## Custom Lint Package
`fg_lint_packages/field_guide_lints/` — 52 rules in 4 categories: architecture (23), data safety (11), sync integrity (10), test quality (8). CI-enforced via `quality-gate.yml`.

## CI/CD
3 workflows in `.github/workflows/`:

| Workflow | Jobs | Purpose |
|----------|------|---------|
| `quality-gate.yml` | Analyze+Test, Architecture Validation, Security Scan | Main pipeline (push + PR) |
| `stale-branches.yml` | 1 | Auto-delete merged branches |
| `labeler.yml` | 1 | Auto-label PRs |

## Database
- **Engine**: sqflite (mobile) + sqflite_common_ffi (desktop)
- **Schema version**: 50
- **Tables**: 36 (core 5, entries 3, contractors 2, personnel 2, quantities 2, photos 1, documents 1, toolbox 4, exports 2, consent 1, support 1, sync 8, extraction 2, certifications 1, storage_cleanup 1)
- **Supabase**: 57 migrations, 1 edge function (`daily-sync-push`), Postgres 17, Realtime enabled

## Domain Rules (lazy-loaded via paths: frontmatter)
| Rule | Loads When |
|------|------------|
| `rules/architecture.md` | Any lib/**/*.dart |
| `rules/platform-standards.md` | Android/iOS config files |
| `rules/frontend/flutter-ui.md` | lib/**/presentation/** |
| `rules/frontend/ui-prototyping.md` | mockups/** |
| `rules/backend/data-layer.md` | lib/**/data/** |
| `rules/backend/supabase-sql.md` | Supabase work |
| `rules/auth/supabase-auth.md` | lib/features/auth/** |
| `rules/pdf/pdf-generation.md` | lib/features/pdf/** |
| `rules/sync/sync-patterns.md` | lib/features/sync/** |
| `rules/database/schema-patterns.md` | lib/core/database/** |
| `rules/testing/patrol-testing.md` | test/**, integration_test/** |

## Quick Reference Commands

**CRITICAL**: Git Bash silently fails on Flutter. ALWAYS use pwsh wrapper.

### Build & Run
1. `pwsh -File tools/build.ps1 -Platform android` — Release APK
2. `pwsh -File tools/build.ps1 -Platform windows` — Windows build
3. `pwsh -File tools/build.ps1 -Platform android -BuildType debug` — Debug APK
4. `pwsh -Command "flutter run -d windows"` — Desktop dev

### Testing & Diagnostics
5. `pwsh -Command "flutter test"` — All tests
6. `pwsh -Command "flutter pub get"` — Get dependencies
7. `pwsh -Command "flutter analyze"` — Static analysis

### Supabase CLI
8. `npx supabase db push` — Push pending migrations to remote
9. `npx supabase db pull` — Pull remote schema changes
10. `npx supabase db diff` — Diff local vs remote schema

### Process Management
11. `pwsh -Command "Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue"` — Kill app ONLY

### Common Mistakes
- NEVER run flutter/dart directly in Git Bash — ALWAYS use `pwsh -Command "..."`
- NEVER use wc, sed, awk, grep as Bash — use Read/Edit/Grep tools instead
- ALWAYS use `-ErrorAction SilentlyContinue` on Stop-Process
- ALWAYS set `timeout: 600000` on `flutter run` commands (default 120s too short)
- ALWAYS quote paths with spaces
- **NEVER run `Stop-Process -Name 'dart'`** — kills MCP servers. Only kill `construction_inspector`.

## Session & Workflow
- `/resume-session` — Load HOT context | `/end-session` — Save state with auto-archiving
- State: `.claude/autoload/_state.md` | Defects: GitHub Issues (labeled by feature/type/priority/layer)
- Git: Feature branches only, never commit to main. `gh pr create` / `gh pr merge --squash`
- Planning pipeline: `brainstorming` (spec) -> `tailor` (research) -> `writing-plans` (plan) -> `implement` (execute)
- **Sizing guide:** XS (single-file mechanical) = no skill needed | S (up to 3 files, known pattern) = skip brainstorming + tailor + writing-plans | M+ = full pipeline. Security-sensitive changes (auth, RLS, sync, data exposure) always require full pipeline regardless of size.

## Pointers (on-demand, NOT auto-loaded)
| What | Where |
|------|-------|
| Agents (13 definitions) | `.claude/agents/` — loaded via skills: frontmatter |
| Skills (12 definitions) | `.claude/skills/` — loaded on-demand by agents or user |
| Directory structure | `.claude/docs/directory-reference.md` |
| Platform requirements | `.claude/rules/platform-standards.md` |
| UI prototyping workflow | `.claude/rules/frontend/ui-prototyping.md` |
| Testing setup & harnesses | `.claude/rules/testing/patrol-testing.md` |
| Detailed project knowledge | `.claude/memory/MEMORY.md` |
| Archives | `.claude/logs/state-archive.md` |
| Audit system (backlogged) | `.claude/backlogged-plans/2026-02-15-audit-system-design.md` |
| Embedded OCR package | `packages/flusseract/` |
| HTTP test driver | `lib/core/driver/` (8 files), entrypoint: `main_driver.dart` |
| Debug log server | `tools/debug-server/server.js` |
| Build & test scripts | `tools/*.ps1`, `scripts/*.ps1` |
| Supabase rollbacks | `supabase/rollbacks/` (manual, partial coverage) |
| Golden tests | `test/golden/` (~95 baseline PNGs) |

## Repositories
| Repo | URL |
|------|-----|
| App Code | https://github.com/Field-Guide/construction-inspector-tracking-app |
| Claude Config | https://github.com/Field-Guide/field-guide-claude-config |
| CodeMunch Fork | https://github.com/RobertoChavez2433/dart_tree_sitter_fork |

`.claude/` is gitignored from app repo and tracked separately.

## Context Efficiency
- **Prefer parallel Agent calls** over `run_in_background`.
- Cap **Explore agents at 3 per session**. Only spawn subagents for 5+ tool-call tasks.
- Don't echo back file contents already in context. Prefer file:line references over code blocks.
- Summarize subagent results in 3-5 bullets, not full output.
