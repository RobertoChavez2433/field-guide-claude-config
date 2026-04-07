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
├── core/       # Cross-cutting: bootstrap, config, database (v50, 36 tables), design_system (~57 components: tokens 6, atoms 11, molecules 8, organisms 12, surfaces 6, feedback 7, layout 5, animation 4 + 4 helpers), di, driver, logging, router, theme
├── shared/     # Base classes, utilities, testing_keys, validators, widgets
├── features/   # 17 feature modules (auth, calculator, contractors, dashboard, entries, forms, gallery, locations, pdf, photos, projects, quantities, settings, sync, todos, toolbox, weather)
└── services/   # Cross-cutting: document, image, permission, photo, soft_delete, startup_cleanup
```

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
- **Design tokens are ThemeExtensions** — `FieldGuideSpacing`, `FieldGuideRadii`, `FieldGuideMotion`, `FieldGuideShadows`, `FieldGuideColors` accessed via `.of(context)`. Two themes only: light + dark (high-contrast theme removed in design system overhaul). Raw `EdgeInsets`, `BorderRadius`, hardcoded `Duration`, and `Colors.*` literals are lint-banned in `lib/**/presentation/**`.
- **Sync-observable controllers** — wizard/long-edit screens extract a `ChangeNotifier` controller and register with `WizardActivityTracker` (`lib/features/sync/application/wizard_activity_tracker.dart`) so `SyncCoordinator` can read in-flight UI state and defer sync that would clobber unsaved drafts.

## Custom Lint Package
`fg_lint_packages/field_guide_lints/` — architecture (33 rules including the 10 design-system rules: `no_raw_button`, `no_raw_divider`, `no_raw_tooltip`, `no_raw_dropdown`, `no_raw_snackbar`, `no_hardcoded_spacing`, `no_hardcoded_radius`, `no_hardcoded_duration`, `no_raw_navigator`, `prefer_design_system_banner`), plus data safety (11), sync integrity (10), test quality (8). CI-enforced via `quality-gate.yml`.

## Database
- **Engine**: sqflite (mobile) + sqflite_common_ffi (desktop)
- **Schema version**: 50
- **Tables**: 36 (core 5, entries 3, contractors 2, personnel 2, quantities 2, photos 1, documents 1, toolbox 4, exports 2, consent 1, support 1, sync 8, extraction 2, certifications 1, storage_cleanup 1)
- **Supabase**: 57 migrations, 1 edge function (`daily-sync-push`), Postgres 17, Realtime enabled

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
8. `pwsh -File tools/start-driver.ps1 -Platform android` — Driver launch; reuses current Android driver build when fresh
9. `pwsh -File tools/start-driver.ps1 -Platform android -ForceRebuild` — Force Android driver rebuild + reinstall
10. `pwsh -File tools/start-driver.ps1 -Platform windows -DriverPort 4949` — Second desktop driver instance for sync verification

### Supabase CLI
11. `npx supabase db push` — Push pending migrations to remote
12. `npx supabase db pull` — Pull remote schema changes
13. `npx supabase db diff` — Diff local vs remote schema

### Process Management
14. `pwsh -Command "Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue"` — Kill app ONLY

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
| Agents (10 definitions) | `.claude/agents/` — role-based agents; domain context is loaded via `.claude/skills/implement/references/worker-rules.md` and `.claude/skills/implement/references/reviewer-rules.md` |
| Skills (12 definitions) | `.claude/skills/` — loaded on-demand by agents or user |
| Directory structure | `.claude/docs/directory-reference.md` |
| Embedded OCR package | `packages/flusseract/` |
| HTTP test driver | `lib/core/driver/` (8 files), entrypoint: `main_driver.dart` |
| Debug log server | `tools/debug-server/server.js` |
| Build & test scripts | `tools/*.ps1`, `scripts/*.ps1` |
| Supabase rollbacks | `supabase/rollbacks/` (manual, partial coverage) |
| Golden tests | `test/golden/` (~95 baseline PNGs) |

## Context Efficiency
- **Prefer parallel Agent calls** over `run_in_background`.
- Cap **Explore agents at 3 per session**. Only spawn subagents for 5+ tool-call tasks.
- Don't echo back file contents already in context. Prefer file:line references over code blocks.
- Summarize subagent results in 3-5 bullets, not full output.
