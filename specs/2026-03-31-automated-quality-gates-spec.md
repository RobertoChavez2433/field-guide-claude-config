# Automated Quality Gates System — Design Spec

**Date**: 2026-03-31
**Status**: Approved
**Replaces**: `.claude/backlogged-plans/2026-02-15-audit-system-design.md` (outdated)
**Scope**: 3-layer quality gate + 4 custom lint packages + GitHub workflow automation

---

## 1. Overview

### Purpose
Automated 3-layer quality gate system that prevents recurring code defects from entering the codebase, enforces established architectural patterns, and reduces Claude token costs by catching issues that linters should handle — not AI.

Built from analysis of 700+ development sessions, 97 documented defects, 8 preprod code reviews, 35+ specs, and 10 rule files. Every rule traces to real bugs that cost real sessions.

### Scope
- **In**: Pre-commit hooks, CI quality gates, branch protection, 4 custom lint packages, GitHub workflow automation (labeling, dependabot, stale branch cleanup, defect sync)
- **Out**: PDF extraction pipeline validation (algorithmic, not lintable), runtime monitoring, release pipeline, account deletion flow

### Success Criteria
- [ ] Zero existing violations when linters are enabled (clean slate)
- [ ] All 4 lint packages show real-time VS Code squiggles
- [ ] Pre-commit hard-blocks on any lint/analyze/test failure
- [ ] CI runs full test suite + architecture + security scanning on every PR
- [ ] Branch protection blocks merge to `main` unless CI passes
- [ ] `.claude/defects/` auto-sync to GitHub Issues
- [ ] PRs auto-labeled by feature area
- [ ] Branches auto-deleted after PR merge
- [ ] Measurable reduction in Claude token spend on pattern-fixing vs feature work

---

## 2. Architecture

### 3-Layer Defense

```
Layer 1: Pre-Commit Hook (local, hard block)
  ├── custom_lint (4 packages, all rules)
  ├── dart analyze (zero errors/warnings)
  ├── flutter test (targeted — changed files only)
  └── grep checks (patterns custom_lint can't catch)
        │
        ▼
Layer 2: GitHub Actions CI (server, comprehensive)
  ├── dart analyze (full project)
  ├── flutter test (all 337+ test files)
  ├── custom_lint (full project)
  ├── architecture validation scripts
  ├── security scanning (RLS, soft-delete, sync safety)
  ├── defect-to-GitHub-Issues sync
  ├── PR auto-labeling
  └── stale branch cleanup
        │
        ▼
Layer 3: Branch Protection (merge gate to main)
  ├── CI must pass before merge
  ├── No direct push to main
  └── Feature branch + PR workflow required
```

### Lint Package Structure

```
fg_lint_packages/
└── field_guide_lints/
    ├── pubspec.yaml
    ├── analysis_options.yaml
    ├── lib/
    │   ├── field_guide_lints.dart         ← plugin entry, registers all rules
    │   ├── architecture/
    │   │   ├── rules/                     ← individual rule files
    │   │   └── architecture_rules.dart    ← barrel export
    │   ├── data_safety/
    │   │   ├── rules/
    │   │   └── data_safety_rules.dart
    │   ├── sync_integrity/
    │   │   ├── rules/
    │   │   └── sync_integrity_rules.dart
    │   └── test_quality/
    │       ├── rules/
    │       └── test_quality_rules.dart
    └── test/                              ← tests for the lint rules themselves
```

### Hook & Script Structure

```
.claude/hooks/
  ├── pre-commit.ps1                ← main orchestrator (replaces current)
  └── checks/
      ├── run-analyze.ps1           ← dart analyze (zero errors/warnings)
      ├── run-custom-lint.ps1       ← custom_lint check
      ├── run-tests.ps1             ← flutter test (targeted — changed files only)
      └── grep-checks.ps1           ← text patterns custom_lint can't catch
```

### CI Structure

```
.github/
  ├── workflows/
  │   ├── quality-gate.yml          ← main CI (analyze, test, lint, security)
  │   ├── labeler.yml               ← PR auto-labeling
  │   ├── sync-defects.yml          ← defect-to-Issues sync
  │   └── stale-branches.yml        ← post-merge branch cleanup
  ├── labeler.yml                   ← label-to-path mapping
  └── dependabot.yml                ← weekly pub dependency updates
```

---

## 3. Design System Reference (Three-Tier Color System)

All lint rules enforcing color usage must reference this verified system:

### Tier 1: `Theme.of(context).colorScheme.*` — Material 3 standard tokens
| Usage | API |
|-------|-----|
| Brand primary | `.primary` |
| Error/destructive | `.error` |
| Primary text | `.onSurface` |
| Secondary/hint text | `.onSurfaceVariant` |
| Elevated surfaces (cards, dialogs) | `.surfaceContainerHigh` |
| Borders, dividers | `.outlineVariant` |
| Brightest surfaces | `.surfaceContainerHighest` |

### Tier 2: `FieldGuideColors.of(context).*` — Domain-specific semantic colors
Defined in `lib/core/theme/field_guide_colors.dart`. Adapts across dark/light/high-contrast.

| Member | Usage |
|--------|-------|
| `surfaceElevated` | Cards, dialogs, bottom sheets |
| `surfaceGlass` | Glassmorphic overlay, frosted panels |
| `surfaceBright` | Active/hover surface, slider tracks |
| `textTertiary` | Hints, disabled labels, timestamps |
| `textInverse` | Text on primary-colored backgrounds |
| `statusSuccess` | Checkmarks, completion badges |
| `statusWarning` | Stale data, sync delays |
| `statusInfo` | Tips, sync status |
| `warningBackground` | Warning banner/chip background |
| `warningBorder` | Warning banner/chip border |
| `shadowLight` | Subtle shadow for elevated surfaces |
| `gradientStart` / `gradientEnd` | Primary gradient colors |
| `accentAmber` | Highlights, badges, stars |
| `accentOrange` | Urgent actions, overdue indicators |
| `dragHandleColor` | Drag handle / reorder grip |

### Tier 3: `AppColors.*` — Static constants (theme-invariant)
Defined in `lib/core/theme/colors.dart`. For domain colors that intentionally don't change with theme.

| Usage | Examples |
|-------|---------|
| Weather icons | `AppColors.weatherSunny`, `.weatherCloudy`, etc. |
| Entry status badges | `AppColors.entryDraft`, `.entryComplete`, `.entrySynced` |
| Photo viewer | `AppColors.photoViewerBg`, `.photoViewerText` |
| Gradients | `AppColors.gradientPrimary`, `.gradientAccent` |

### Deprecated (MUST NOT USE)
- `AppTheme.*` color constants — marked `@Deprecated` in `lib/core/theme/app_theme.dart`
- Direct `Colors.*` from Flutter material (except `Colors.transparent` where semantically appropriate)

---

## 4. DI System Reference

### Current State (Incomplete — Needs Cleanup)
- `AppInitializer.initialize()` → returns `AppDependencies` container
- `AppDependencies` aggregates: `CoreDeps`, `AuthDeps`, `ProjectDeps`, `EntryDeps`, `FormDeps`, `SyncDeps`, `FeatureDeps`
- `buildAppProviders(AppDependencies deps)` composes the Provider tree

### Intended Pattern (What Linters Enforce)
- **Supabase client**: Resolved ONCE in DI root, injected via constructor to all consumers. `Supabase.instance.client` is a violation anywhere.
- **DatabaseService**: Created ONCE in `AppInitializer`, injected via constructor. Direct `DatabaseService()` construction is a violation outside DI root.
- **Services**: Constructed in DI root, injected via constructor. No `PermissionService()`, `ImageService()`, etc. in widgets or feature code.
- **Providers**: All registered in `buildAppProviders()`. No provider splicing in `main.dart` or other files.

---

## 5. Lint Rules — Architecture Linter (17 rules)

| # | Rule | Severity | Current Violations | Detection |
|---|------|----------|-------------------|-----------|
| A1 | `avoid_supabase_singleton` — no `Supabase.instance.client` anywhere outside DI root | ERROR | 15 across 7 files | AST |
| A2 | `no_direct_database_construction` — no `DatabaseService()` outside DI root | ERROR | 3 violations | AST |
| A3 | `no_raw_sql_in_presentation` — no db.query/rawQuery in presentation/ | ERROR | 0 (clean) | AST+path |
| A4 | `no_raw_sql_in_di` — no db.query/rawQuery/transactions in di/ files | ERROR | 1 (sync_providers) | AST+path |
| A5 | `no_datasource_import_in_presentation` — block datasource imports from presentation | ERROR | Multiple | Import path |
| A6 | `no_business_logic_in_di` — no await/try-catch/transactions in di/ files | WARNING | sync_providers | AST |
| A7 | `single_composition_root` — Provider construction only in buildAppProviders() | WARNING | main.dart splicing | AST |
| A8 | `no_service_construction_in_widgets` — no `PermissionService()` etc. in widgets | WARNING | Multiple | AST |
| A9 | `no_silent_catch` — catch blocks must contain Logger call | WARNING | 20 across 9 files (excl. Logger's own 10) | AST |
| A10 | `max_file_length` — warn >500, error >1000 lines | WARN/ERR | 43 files >500, 14 >1000 | Line count |
| A11 | `max_import_count` — warn >25, error >40 imports | WARN/ERR | app_initializer 101 imports | Count |
| A12 | `no_deprecated_app_theme` — no `AppTheme.*` color constants | ERROR | 797 across 76 files | AST |
| A13 | `no_hardcoded_colors` — no `Colors.*` in presentation (except transparent) | WARNING | 8 real violations | AST+path |
| A14 | `no_hardcoded_form_type` — no `'mdot_0582b'` string literals outside registry | WARNING | 29 locations | Grep |
| A15 | `no_duplicate_service_instances` — same class constructed 2+ times in DI | WARNING | Historical (S479, S506) | AST |
| A16 | `annotate_overrides` — enable built-in rule | WARNING | 80+ missing | Built-in |
| A17 | `no_async_lifecycle_without_await` — async callbacks must be awaited | WARNING | 3 sessions (S479, S508) | AST |

---

## 6. Lint Rules — Data Safety Linter (12 rules)

| # | Rule | Severity | Current Violations | Detection |
|---|------|----------|-------------------|-----------|
| D1 | `avoid_raw_database_delete` — no `database.delete()` outside SoftDeleteService/GenericLocalDatasource/sync engine | ERROR | 34 across 20 files (audit each) | AST |
| D2 | `require_soft_delete_filter` — raw `database.query()` bypassing GenericLocalDatasource must include `deleted_at IS NULL` | ERROR | Audit needed | AST |
| D3 | `avoid_unguarded_firstwhere` — `.firstWhere()` must have `orElse` | ERROR | 0 current (preventive) | AST |
| D4 | `tomap_field_completeness` — toMap() must include all constructor params except `deleted_at`/`deleted_by` (managed by sync engine) | WARNING | Audit needed | AST |
| D5 | `require_mounted_check_after_async` — context use after await needs `if (!mounted) return` | ERROR | ~10 violations | AST |
| D6 | `copywith_nullable_sentinel` — copyWith with `??` on nullable params must use sentinel pattern | WARNING | Historical (S338, S348) | AST |
| D7 | `check_bytes_null_and_empty` — Uint8List null check must also check `.isEmpty` | WARNING | Historical (S306) | AST |
| D8 | `no_sentinel_strings_in_data` — no `'--'` in model/data fields | WARNING | 1 active defect | Grep |
| D9 | `schema_column_consistency` — fromMap keys must match SQL DDL columns | ERROR | CI script (cross-file) | CI script |
| D10 | `migration_column_before_index` — column must exist before index/trigger in migrations | ERROR | Historical (S507) | Grep/SQL |
| D11 | `migration_requires_if_exists` — ALTER TABLE needs IF EXISTS guard | WARNING | Historical (S454, S492) | Grep/SQL |
| D12 | `path_traversal_guard` — no `path.contains('..')` as sole traversal guard | ERROR | 1 security defect | Grep |

---

## 7. Lint Rules — Sync Integrity Linter (9 rules)

| # | Rule | Severity | Current Violations | Detection |
|---|------|----------|-------------------|-----------|
| S1 | `conflict_algorithm_ignore_guard` — must check rowId==0 after ConflictAlgorithm.ignore (sync engine already has this; targets 7 other usages) | ERROR | 7 without fallback | AST |
| S2 | `change_log_cleanup_requires_success` — no unconditional change_log wipe | ERROR | BUG-S09 pattern | AST/Grep |
| S3 | `sync_control_inside_transaction` — pulling flag must be set inside transaction | ERROR | Historical (BUG-S09) | Grep |
| S4 | `no_sync_status_column` — no `sync_status` in schema/models (deprecated pattern) | ERROR | BLOCKER-27 pattern | Grep |
| S5 | `tomap_includes_project_id` — synced child models must include project_id in toMap() | ERROR | 0 current (fixed, preventive) | AST |
| S6 | `no_state_reload_after_rpc` — Supabase RPC calls must refresh local state | WARNING | Historical (S454, S472) | AST |
| S7 | `cached_connectivity_recheck` — `_isOnline` must recheck before use | WARNING | Historical (S587, BLOCKER-18) | AST |
| S8 | `sync_time_on_success_only` — _lastSyncTime only updated in success path | WARNING | Historical (S511) | AST |
| S9 | `rls_column_must_exist` — RLS policy columns must exist in target table | ERROR | Historical (S492, S558) | SQL script |

---

## 8. Lint Rules — Test Quality Linter (8 rules)

| # | Rule | Severity | Current Violations | Detection |
|---|------|----------|-------------------|-----------|
| T1 | `no_hardcoded_key_in_widgets` — use TestingKeys, not `Key('...')` in runtime code | WARNING | 12 across 5 files | AST |
| T2 | `no_hardcoded_key_in_tests` — use TestingKeys in test code | WARNING | Audit needed | AST |
| T3 | `no_hardcoded_delays_in_tests` — no `Future.delayed` in tests | WARNING | 63 across 7 files | Grep |
| T4 | `no_skip_without_issue_ref` — `skip:` must reference a bug/issue | INFO | 12 skips without refs | AST |
| T5 | `no_ignore_for_file_in_tests` — no lint suppressions in test/ | WARNING | 32 suppressions | Grep |
| T6 | `no_stale_patrol_references` — no patrol/flutter_driver imports | WARNING | pubspec + 2 files | Import |
| T7 | `no_direct_testing_keys_bypass` — only `TestingKeys.*` facade in runtime code | WARNING | 41 bypasses in 12 files | Import path |
| T8 | `require_did_update_widget_for_controllers` — StatefulWidget with controller needs didUpdateWidget | ERROR | 1 (SearchBarField) | AST |

---

## 9. Additional CI/Grep Checks (scripts, not custom_lint)

| Check | Detection | Layer |
|-------|-----------|-------|
| FK indexes exist for all REFERENCES columns | SQL parse | CI |
| No `AUTOINCREMENT` in schema | Grep | CI |
| change_log trigger count (20) ≈ adapter count (22, minus 2 push-only) | Cross-ref | CI |
| Deprecated screen exports (FormsListScreen, FormFillScreen) | Grep | CI |
| Dead barrel exports (zero consumers) | Import analysis | CI |
| `sync_control` writes outside transaction blocks | Grep | Pre-commit |
| `change_log` DELETE without success guard | Grep | Pre-commit |
| `0.85`/`0.65`/`0.45` bare threshold literals | Grep | Pre-commit |
| `'mdot_0582b'` outside builtin_forms.dart | Grep | Pre-commit |
| `ALTER TABLE` without `IF EXISTS` in .sql files | Grep | Pre-commit |

---

## 10. Pre-Commit Hook Design

**Location**: `.claude/hooks/pre-commit.ps1` (replaces current), called via `.githooks/pre-commit` bash shim.

**Orchestrator behavior:**
1. Get staged `.dart` files (skip generated: `.g.dart`, `.freezed.dart`, `.mocks.dart`)
2. Run checks in sequence: analyze → custom_lint → grep checks → targeted tests
3. ANY failure = hard block, exit 1
4. All pass = exit 0

**Test targeting logic:**
```
Source: lib/features/{feature}/.../{file}.dart
  → Test: test/features/{feature}/.../{file}_test.dart
```
Only run tests for changed files. If no matching test file exists, skip (CI runs full suite).

**Grep checks** (patterns custom_lint can't catch):
- `sync_control` writes outside transaction blocks
- `change_log` DELETE without success guard
- `0.85`/`0.65`/`0.45` bare threshold literals
- `'mdot_0582b'` outside builtin_forms.dart
- `AUTOINCREMENT` in schema files
- `ALTER TABLE` without `IF EXISTS` in `.sql` files

---

## 11. GitHub Actions CI Design

### Workflow: `quality-gate.yml`
**Triggers:** Push to any branch, PR to main

**Job 1: `analyze-and-test`** (~5 min)
- `flutter pub get`
- `dart analyze` (zero errors — NO `--no-fatal-infos` flag)
- `custom_lint` check (all 46 rules)
- `flutter test` (full suite, all 337+ test files)

**Job 2: `architecture-validation`** (~1 min, parallel with Job 1)
- FK index verification (SQL parse)
- No AUTOINCREMENT in schema
- change_log trigger count = adapter count
- Dead barrel export detection
- Deprecated screen export check
- Schema column consistency (fromMap keys vs DDL)
- RLS column existence validation

**Job 3: `security-scanning`** (~1 min, parallel)
- Supabase singleton usage audit (must be zero outside DI root)
- Raw database.delete() outside SoftDeleteService (must be zero)
- Path traversal guard audit
- sync_control transaction boundary check
- change_log cleanup success-guard check

### Workflow: `labeler.yml`
Auto-labels PRs by changed file paths:
```yaml
sync: ['lib/features/sync/**']
pdf: ['lib/features/pdf/**']
auth: ['lib/features/auth/**']
database: ['lib/core/database/**']
ui: ['lib/features/*/presentation/**']
tests: ['test/**']
config: ['.github/**', 'analysis_options.yaml', 'pubspec.yaml']
```

### Workflow: `sync-defects.yml`
**Trigger:** Push to main
- Parses `.claude/defects/_defects-*.md` files
- Creates/updates GitHub Issues with feature labels
- Closes issues when defects are archived

### Workflow: `stale-branches.yml`
**Trigger:** PR merge
- Auto-deletes the source branch after merge

### File: `dependabot.yml`
```yaml
version: 2
updates:
  - package-ecosystem: "pub"
    directory: "/"
    schedule:
      interval: "weekly"
    labels: ["dependencies"]
```

### Cleanup: Delete existing broken workflows
- `.github/workflows/e2e-tests.yml` — replace with `quality-gate.yml`
- `.github/workflows/nightly-e2e.yml` — delete (fully deprecated)

---

## 12. Branch Protection

**Rules for `main`:**

| Rule | Value |
|------|-------|
| Require status checks before merging | Yes |
| Required checks | `analyze-and-test`, `architecture-validation`, `security-scanning` |
| Require branches to be up to date | Yes |
| Block direct pushes | Yes |
| Allow force pushes | No |
| Auto-delete head branches | Yes |

**Developer workflow:**
```
git checkout main && git pull
git checkout -b feature/my-feature
[implement, commit — pre-commit hook validates each commit]
git push -u origin feature/my-feature
gh pr create --title "feat: ..." --body "..."
[CI runs automatically, auto-labels applied]
[Fix any CI failures, push again]
gh pr merge --squash
[Branch auto-deleted]
git checkout main && git pull
```

---

## 13. Clean Slate Strategy

### Phase 1 — analysis_options.yaml Hardening
- Upgrade from `flutter_lints: ^6.0.0` to current `lints` package
- Enable: `avoid_print`, `annotate_overrides`, `unnecessary_overrides`, `unused_import`, `unused_field`
- Upgrade `deprecated_member_use_from_same_package` to error
- Ensure `use_build_context_synchronously` is error
- Remove `--no-fatal-infos` from CI workflow
- Fix all violations these surface

### Phase 2 — Bulk Violation Cleanup (verified counts)

| Violation | Count | Cleanup Approach |
|-----------|-------|-----------------|
| `AppTheme.*` constants | 797 across 76 files | Mass replace → `Theme.of(context).colorScheme.*` / `FieldGuideColors.of(context).*` / `AppColors.*` per Section 3 three-tier system |
| `.first` without guard | 158 across 70 files | Audit each: replace with `.firstOrNull` where list could be empty |
| `catch (_)` without logging | 20 across 9 files | Add `Logger.<category>()` calls (categories: sync, pdf, db, auth, ocr, nav, ui, photo, lifecycle, bg, error) |
| `Supabase.instance.client` | 15 across 7 files | Complete DI migration — resolve once in AppInitializer, inject via constructor everywhere |
| `DatabaseService()` direct | 3 violations | Inject via DI in background_sync_handler, user_profile_sync_datasource, pdf_import_service |
| Hardcoded `Key('...')` in runtime | 12 across 5 files | Replace with `TestingKeys.*` references |
| `*TestingKeys.*` bypasses | 41 across 12 files | Replace with `TestingKeys.*` facade |
| `context.read` after await without mounted | ~10 instances | Add `if (!mounted) return;` guards |
| `ConflictAlgorithm.ignore` without fallback | 7 usages outside sync engine | Add rowId==0 check with UPDATE fallback |
| `Future.delayed` in tests | 63 across 7 files | Replace with proper async test patterns |
| Hardcoded `Colors.*` | 8 real violations | Replace with theme tokens |
| Files >1000 lines | 14 files | Decompose incrementally (WARNING severity — not a Phase 2 blocker) |

### Phase 3 — Install and Enable custom_lint
- Add `custom_lint` and `custom_lint_builder` to dev_dependencies
- Create `fg_lint_packages/field_guide_lints/` with all 46 rules
- Zero violations at this point — any new violation immediately blocks commit

### Phase 4 — Deploy CI and Branch Protection
- Delete broken `e2e-tests.yml` and `nightly-e2e.yml`
- Deploy `quality-gate.yml`, `labeler.yml`, `sync-defects.yml`, `stale-branches.yml`
- Create `.github/labeler.yml`, `.github/dependabot.yml`
- Configure branch protection on `main`
- Verify full workflow: branch → commit → push → PR → CI → merge

---

## 14. Key Reference Files

| File | Purpose |
|------|---------|
| `lib/core/theme/field_guide_colors.dart` | FieldGuideColors ThemeExtension (16 semantic colors) |
| `lib/core/theme/colors.dart` | AppColors static constants |
| `lib/core/theme/app_theme.dart` | Deprecated color aliases (migration source) |
| `lib/core/di/app_initializer.dart` | DI root — AppDependencies container |
| `lib/core/di/app_providers.dart` | Provider tree composition |
| `lib/services/soft_delete_service.dart` | SoftDeleteService (cascade, purge, hardDelete) |
| `lib/shared/datasources/generic_local_datasource.dart` | Base datasource with built-in `_notDeletedFilter` |
| `lib/core/logging/logger.dart` | Logger with category methods (sync, pdf, db, auth, etc.) |
| `lib/shared/testing_keys/testing_keys.dart` | TestingKeys facade (delegates to 15 sub-key files) |
| `lib/features/sync/engine/sync_registry.dart` | SyncRegistry — 22 adapters in FK dependency order |
| `lib/features/sync/engine/change_tracker.dart` | change_log queries (has retry_count filter) |
| `lib/features/sync/engine/sync_engine.dart` | Sync engine (has ConflictAlgorithm.ignore + rowId==0 fallback) |
| `lib/core/database/schema/sync_engine_tables.dart` | change_log schema, triggers for 20 tables |

---

## 15. Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| 3 enforcement layers | Pre-commit + CI + branch protection | Full coverage, fast local feedback |
| Pre-commit strictness | Hard block on all failures | User wants strict — clean slate, no exceptions |
| Lint technology | `custom_lint` by Remi Rousselet | Mature, VS Code squiggles, community standard |
| 4 lint packages | Architecture, Data Safety, Sync Integrity, Test Quality | Separate concerns, independent strictness |
| Package location | `fg_lint_packages/` in app repo | Must be resolvable by dart analyze |
| Scripts location | `.claude/hooks/` | Consistent with existing tooling location |
| Clean slate approach | Fix all violations before enabling | Pre-production cleanup happening now anyway |
| Lint package `flutter_lints` | Upgrade to current `lints` | `flutter_lints: ^6.0.0` is older/deprecated |
| CI analyzer flag | Remove `--no-fatal-infos` | Info-level diagnostics should block CI |
| `is_deleted` column | Does NOT exist — stale documentation | Only `deleted_at` / `deleted_by` are used |
| Soft-delete in toMap() | Intentionally excluded | Managed by sync engine / SoftDeleteService directly |
| retry_count filter | Already implemented | change_tracker.dart has `retry_count < maxRetryCount` |
| ConflictAlgorithm.ignore fallback | Exists in sync engine only | 7 other usages need the fallback added |

---

## 16. Constraints to Update (Post-Implementation)

These rule/doc files need updating to match verified reality:

| File | Update Needed |
|------|---------------|
| `.claude/rules/database/schema-patterns.md` | Remove `is_deleted INTEGER DEFAULT 0` — column doesn't exist. Only `deleted_at`/`deleted_by`. |
| `.claude/rules/architecture.md` | Add anti-patterns: Supabase singleton, DatabaseService() direct, service construction in widgets, business logic in di/ files, Provider splicing outside buildAppProviders() |
| `.claude/rules/frontend/flutter-ui.md` | Add accessibility section (48dp touch targets, Semantics labels). Strengthen color rule with lint enforcement reference. Add dark mode testing requirement. |
| `.claude/rules/sync/sync-patterns.md` | Add: sync_control flag MUST be inside transaction. change_log cleanup MUST be conditional on RPC success. ConflictAlgorithm.ignore MUST have rowId==0 fallback. |
| `.claude/rules/testing/patrol-testing.md` | Add deprecated stacks section (patrol, flutter_driver). Update 3-tier testing description. |
| `analysis_options.yaml` | Complete rewrite — currently empty. |
| `.github/workflows/e2e-tests.yml` | Delete and replace with quality-gate.yml. |
| `.github/workflows/nightly-e2e.yml` | Delete (fully deprecated). |
