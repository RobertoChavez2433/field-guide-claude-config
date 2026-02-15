# Automated Audit System — Design Plan

**Date**: 2026-02-15
**Status**: Approved
**Scope**: 3-layer quality gate system + GitHub workflow modernization

---

## Overview

### Purpose
An automated 3-layer quality gate system that prevents the 68 recurring code issues (identified across 300+ sessions of code reviews) from ever reaching the `main` branch. Eliminates manual pre-commit checks and reduces code review token usage by 30-50%.

### Success Criteria
- [ ] Zero manual grep checks before committing (all automated)
- [ ] Zero "we caught this in code review again" for the 68 known patterns
- [ ] `main` branch always passes all checks (branch protection enforced)
- [ ] New anti-patterns discovered in sessions get added to the system incrementally
- [ ] Defects in `.claude/defects/` auto-sync to GitHub Issues
- [ ] PRs auto-labeled by feature area

### Approach: Hybrid (Grep + Custom Lint)
- **Grep scripts** for ~35 text-matchable pattern checks (immediate value)
- **Custom Dart lint rules** (`custom_lint` package) for ~25 structural/semantic checks (incremental)
- Both run via pre-commit hooks and CI

### CLAUDE.md Note
Add to CLAUDE.md: Each session, check for new anti-patterns discovered during work. Suggest additions to the lint system with rationale. User decides whether to add as grep check, custom lint rule, or skip.

---

## Architecture

### 3-Layer Defense

```
Layer 1: Pre-Commit Hook (local, ~1-2 min)
  ├── Grep-based pattern checks (~35 checks, ~10 sec)
  ├── dart analyze (zero errors required)
  └── flutter test (changed files only)
        │
        ▼
Layer 2: GitHub Actions CI (server, ~5 min)
  ├── Full test suite (700+ tests)
  ├── Coverage threshold enforcement
  ├── Custom validation scripts (duplicates, architecture, complexity)
  ├── Complexity report posted as PR comment
  └── Auto-labeling
        │
        ▼
Layer 3: Branch Protection (gate to main)
  ├── CI must pass before merge
  ├── No direct push to main
  └── Feature branch + PR workflow required
```

---

## Layer 1: Pre-Commit Hook (Local)

### Structure
```
.git/hooks/pre-commit              ← Entry point (symlinks to tools/audit/)
tools/audit/
  ├── pre-commit.sh                ← Main orchestrator
  ├── setup-hooks.sh               ← One-time installer (creates symlink)
  ├── checks/
  │   ├── crash-risks.sh           ← firstWhere, .first, empty collection
  │   ├── banned-patterns.sh       ← deprecated imports, debugPrint, DI bypass
  │   ├── constants-enforcement.sh ← hardcoded thresholds, string matching
  │   ├── file-health.sh           ← file size limits, barrel export check
  │   └── analyzer-and-tests.sh    ← dart analyze + targeted flutter test
  └── config/
      └── exclusions.txt           ← Files/patterns to exclude from checks
```

### Check Details

#### crash-risks.sh (Severity: BLOCK)
| # | Pattern | Grep Command | Issue Ref |
|---|---------|-------------|-----------|
| 1 | `.firstWhere(` without `orElse` | `grep -n '\.firstWhere(' \| grep -v 'orElse'` | Crash: 13+ instances |
| 2 | `.first` on non-literal lists | `grep -n '\.first[^W]'` (exclude firstWhere) | Crash: empty list |
| 3 | `bytes == null` without `bytes.isEmpty` | Context-aware check | Crash: empty Uint8List |
| 4 | `.single` without length check | `grep -n '\.single[^t]'` | Crash: 0 or 2+ elements |

#### banned-patterns.sh (Severity: BLOCK)
| # | Pattern | Grep Command | Issue Ref |
|---|---------|-------------|-----------|
| 5 | Import from `deprecated/` | `grep -n "import.*deprecated/"` | Dead test: 1,800 lines |
| 6 | `debugPrint(` in lib/ | `grep -n 'debugPrint('` | Logging: 485+ calls |
| 7 | `DatabaseService()` in presentation/ | `grep -n 'DatabaseService()'` | DI bypass: 2 screens |
| 8 | `dynamic` in mock overrides | `grep -n 'dynamic'` in test helpers | Type safety loss |
| 9 | V1 stage imports in V2 files | `grep -n "import.*stages/(document_analyzer\|native_extractor\|structure_preserver)"` | V2 constraint |

#### constants-enforcement.sh (Severity: BLOCK)
| # | Pattern | Grep Command | Issue Ref |
|---|---------|-------------|-----------|
| 10 | Bare threshold `0.85\|0.65\|0.45` | `grep -En '0\.(85\|65\|45)' \| grep -v 'Thresholds\|const\|test'` | Drift: 4+ files |
| 11 | `stageName.contains(` | `grep -n 'stageName\.contains\|\.contains.*[Ss]tage'` | String matching |
| 12 | Regex redefinitions | `grep -n '_itemNumberPattern\|_currencyPattern'` in multiple files | Pattern drift |
| 13 | `_headerKeywords` duplication | `grep -n '_headerKeywords'` in multiple files | Keyword drift |

#### file-health.sh (Severity: WARN at 1500, BLOCK at 2500)
| # | Check | Command | Issue Ref |
|---|-------|---------|-----------|
| 14 | File > 1,500 lines | `wc -l` on changed files | God classes |
| 15 | File > 2,500 lines | `wc -l` on changed files | God classes (block) |
| 16 | Orphaned files (in dir but not barrel) | Compare `ls` vs barrel `export` | Stale files |

#### analyzer-and-tests.sh (Severity: BLOCK)
| # | Check | Command | Issue Ref |
|---|-------|---------|-----------|
| 17 | `dart analyze` | `pwsh -Command "dart analyze lib/"` | Zero errors required |
| 18 | Targeted tests | Map changed files → test files, run only those | Fast feedback |

### Changed-File Test Mapping
```
Source: lib/features/{feature}/.../{file}.dart
  → Test: test/features/{feature}/.../{file}_test.dart

Source: lib/features/pdf/services/extraction/stages/{stage}.dart
  → Test: test/features/pdf/extraction/stages/stage_*_{stage}_test.dart
```

---

## Layer 2: GitHub Actions CI

### Workflows

#### DELETE (broken, outdated)
- `.github/workflows/e2e-tests.yml`
- `.github/workflows/nightly-e2e.yml`

#### CREATE: `.github/workflows/quality-gate.yml`
**Triggers**: Push to any branch, PR to main

**Job 1: analyze-and-test** (~3 min)
```yaml
steps:
  - flutter analyze (full project)
  - flutter test (ALL tests)
  - Upload coverage to Codecov
  - Fail if coverage < threshold
```

**Job 2: custom-validation** (~1 min, parallel)
```yaml
steps:
  - Duplicate code detection script
  - Architecture layer validation (features have data/presentation)
  - Barrel export completeness check
  - Regex pattern consistency check
  - Stale reference detection (doc comments → deleted classes)
  - toMap/fromMap round-trip consistency
```

**Job 3: complexity-report** (~30 sec, parallel)
```yaml
steps:
  - Lines per file report (flag > 1,500)
  - Methods per class (flag > 30)
  - Constructor params (flag > 10)
  - Post as PR comment via gh pr comment
```

#### CREATE: `.github/workflows/labeler.yml`
Auto-labels PRs based on changed file paths.

#### CREATE: `.github/labeler.yml`
```yaml
pdf:
  - 'lib/features/pdf/**'
  - 'test/features/pdf/**'
sync:
  - 'lib/features/sync/**'
ui:
  - 'lib/features/*/presentation/**'
extraction:
  - 'lib/features/pdf/services/extraction/**'
tests:
  - 'test/**'
config:
  - '.github/**'
  - 'analysis_options.yaml'
  - 'pubspec.yaml'
database:
  - 'lib/core/database/**'
auth:
  - 'lib/features/auth/**'
```

#### CREATE: `.github/dependabot.yml`
```yaml
version: 2
updates:
  - package-ecosystem: "pub"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
```

#### CREATE: `codecov.yml`
```yaml
coverage:
  status:
    project:
      default:
        target: auto
        threshold: 2%  # Fail if coverage drops by more than 2%
```

### Custom Validation Scripts
```
tools/audit/ci/
  ├── duplicate-detection.sh     ← Find identical method bodies
  ├── architecture-check.sh      ← Verify feature layer structure
  ├── barrel-completeness.sh     ← Every .dart in dir is exported
  ├── regex-consistency.sh       ← All regex definitions match
  ├── stale-references.sh        ← Doc comments reference existing classes
  └── complexity-report.sh       ← Lines/methods/params per file
```

---

## Layer 3: Branch Protection + PR Workflow

### Branch Protection Rules (main)
| Rule | Value |
|------|-------|
| Require status checks before merging | Yes |
| Required checks | `analyze-and-test`, `custom-validation` |
| Require branches to be up to date | Yes |
| Block direct pushes | Yes |

### New Developer Workflow
```
1. git checkout main && git pull
2. git checkout -b feature/my-feature
3. [implement, commit, iterate — pre-commit hook validates each commit]
4. git push -u origin feature/my-feature
5. gh pr create --title "feat: ..." --body "..."
6. [CI runs automatically, auto-labels applied]
7. [Fix any CI failures, push again]
8. gh pr merge --squash
9. git checkout main && git pull
10. git branch -d feature/my-feature
```

### GitHub MCP Setup
- Research and install a GitHub MCP server for Claude Code
- Enables: branch protection configuration, rich PR comments, CI log access
- Fallback: Use `gh` CLI for all operations (already functional)

---

## Layer 4: Defect Sync + Custom Lint

### Defect-to-GitHub-Issues Sync
```
tools/audit/sync-defects.sh
```
- Parses `.claude/defects/_defects-*.md` files
- Creates/updates GitHub Issues with feature labels
- Closes issues when defects are archived
- Runs via `.github/workflows/sync-defects.yml` on push to main

### Custom Lint Package
```
packages/field_guide_lints/
  ├── pubspec.yaml
  ├── lib/
  │   ├── field_guide_lints.dart         ← Plugin entry point
  │   └── rules/
  │       ├── avoid_first_where.dart     ← Rule 1
  │       ├── require_mounted_check.dart ← Rule 2
  │       └── avoid_incomplete_eq.dart   ← Rule 3
  └── analysis_options.yaml
```

**Initial 3 rules**:
1. `avoid_first_where_without_or_else` — Flags `.firstWhere()` without `orElse` parameter
2. `require_mounted_check_after_await` — Flags setState/context usage after await without mounted check
3. `avoid_incomplete_equality` — Flags `==` operators that don't check all constructor fields

---

## Implementation Phases

### Phase 1: Foundation (Pre-commit hook + repo cleanup)
**Branch**: `chore/audit-system-foundation`
**Agent**: General implementation (main Claude session)
**Scope**:
1. Create `tools/audit/` directory structure
2. Write 5 check scripts (crash-risks, banned-patterns, constants-enforcement, file-health, analyzer-and-tests)
3. Create `tools/audit/pre-commit.sh` orchestrator
4. Create `tools/audit/setup-hooks.sh` installer
5. Delete broken `.github/workflows/e2e-tests.yml`
6. Delete broken `.github/workflows/nightly-e2e.yml`
7. Add lint suggestion note to `.claude/CLAUDE.md`
8. Test: Run pre-commit hook manually, verify it catches known issues
**Files**: ~12 new, ~3 modified

### Phase 2: GitHub Actions CI
**Branch**: `chore/quality-gate-ci`
**Agent**: General implementation
**Scope**:
1. Create `.github/workflows/quality-gate.yml` (3 parallel jobs)
2. Create `tools/audit/ci/` validation scripts (6 scripts)
3. Create `.github/labeler.yml` + `.github/workflows/labeler.yml`
4. Create `.github/dependabot.yml`
5. Create `codecov.yml`
6. Test: Push branch, verify CI runs and posts results
**Files**: ~12 new

### Phase 3: Branch Protection + GitHub MCP
**Branch**: `chore/branch-protection-setup`
**Agent**: General implementation
**Scope**:
1. Research GitHub MCP options (official vs community)
2. Install and configure GitHub MCP for Claude Code
3. Configure branch protection on `main` via MCP or web UI
4. Test full workflow: branch → commit → push → PR → CI → merge
5. Document new workflow in `.claude/docs/guides/pr-workflow-guide.md`
**Files**: ~3-5 new/modified

### Phase 4: Defect Sync + Custom Lint Skeleton
**Branch**: `chore/defect-sync-and-lint-setup`
**Agent**: General implementation
**Scope**:
1. Create `tools/audit/sync-defects.sh` parser script
2. Create `.github/workflows/sync-defects.yml`
3. Create `packages/field_guide_lints/` package skeleton
4. Write 3 initial custom lint rules
5. Integrate into `analysis_options.yaml`
6. Test: Verify defects create issues, lint rules flag in IDE
**Files**: ~15 new, ~2 modified

### Phase 5: Tuning & Documentation
**Branch**: `chore/audit-system-tuning`
**Agent**: qa-testing-agent, code-review-agent
**Scope**:
1. Run full system on current codebase, catalog false positives
2. Add exclusion entries for known exceptions
3. Tune thresholds (file size, coverage %, complexity)
4. Create contributing guide for adding new checks
5. Update `.claude/CLAUDE.md` with new workflow commands
6. Final verification: full end-to-end test
**Files**: ~5 modified

---

## The 68 Automatable Checks — Full Reference

### Pre-Commit (Grep-Based) — 35 Checks

**Crash Risks (4)**:
1. `.firstWhere()` without `orElse`
2. `.first` on non-literal lists
3. Null-only check on collections (missing `.isEmpty`)
4. `.single` without length guard

**Banned Patterns (5)**:
5. `import.*deprecated/` in non-deprecated files
6. `debugPrint(` in lib/ (use AppLogger)
7. `DatabaseService()` in presentation/
8. `dynamic` in test mock overrides
9. V1 stage imports in V2 files

**Constants Enforcement (4)**:
10. Bare threshold floats (0.85/0.65/0.45) outside constants
11. `stageName.contains(` (use StageNames.*)
12. Duplicate regex patterns (_itemNumberPattern, _currencyPattern)
13. Duplicate keyword lists (_headerKeywords)

**File Health (3)**:
14. File > 1,500 lines (warn)
15. File > 2,500 lines (block)
16. Files not in barrel export

**Standard Quality (2)**:
17. `dart analyze` errors
18. Targeted test failures

**Additional Grep Patterns (17)**:
19. `Stopwatch` in classes marked `@immutable`
20. `Future.delayed` in production code (test anti-pattern)
21. `print(` in lib/ (should be logger)
22. `TODO` without issue reference
23. Hardcoded PSM values outside config
24. `pumpAndSettle()` in tests (flaky)
25. `Key(` hardcoded in widgets (use TestingKeys)
26. `setState` after `await` without `mounted` check
27. `for.*in.*` + `repository.` pattern (N+1 query risk)
28. Constructor with > 15 parameters
29. `@Deprecated` methods (flag for review)
30. `// ignore:` annotations (flag for review)
31. Duplicate class names across files
32. Import from `package:` pointing to deprecated path
33. `catch (e)` without type (too broad)
34. `as dynamic` cast
35. `late` variables in StatelessWidget

### CI-Only (Custom Scripts) — 25 Checks

**Duplicate Detection (8)**:
36. Identical method bodies across files
37. Identical save() pattern across repositories
38. Identical pull/push methods in SyncService
39. Duplicate median implementations
40. Duplicate regex pattern definitions with inconsistencies
41. Duplicate header keyword lists
42. Duplicate OcrElement construction in tests
43. Provider boilerplate not extending BaseListProvider

**Architecture (6)**:
44. Feature missing data/ or presentation/ layer
45. Feature directory > 50 files
46. Cross-module barrel imports
47. Barrel export missing files in directory
48. Direct service instantiation (not via DI)
49. Screen files > 30 methods

**Serialization (3)**:
50. toMap/fromMap field completeness (round-trip test)
51. == operator missing constructor fields
52. hashCode inconsistent with ==

**Complexity (4)**:
53. File line count report
54. Method count per class
55. Constructor parameter count
56. Cyclomatic complexity (if available)

**Stale References (4)**:
57. Doc comments referencing deleted/renamed classes
58. Test files referencing moved source files
59. Config referencing non-existent paths
60. Plan files referencing completed/archived items

### Custom Lint (AST-Based) — 8 Checks (incremental)

61. `avoid_first_where_without_or_else` — AST-verified, zero false positives
62. `require_mounted_check_after_await` — Detects setState/context after await
63. `avoid_incomplete_equality` — Compares constructor fields vs == fields
64. `avoid_mutable_in_immutable` — Stopwatch in @immutable class
65. `require_empty_check_after_null` — Collection needs both null + isEmpty
66. `avoid_loop_queries` — DB calls inside for loops
67. `require_exhaustive_switch` — Switch on enum misses cases
68. `avoid_broad_catch` — catch(e) without specific type

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layer distribution | Pre-commit + CI + branch protection | Full coverage, fast feedback locally |
| Pre-commit speed | Include tests (1-2 min) | User prefers strong local enforcement |
| Lint approach | Hybrid (grep + custom_lint) | Immediate value + incremental learning |
| Git workflow | Feature branches + PRs | Industry standard, protects main |
| Branch protection | CI must pass | Simple starting point, can tighten later |
| Old workflows | Delete and rebuild | Existing workflows never worked |
| GitHub MCP | Include in plan | Enables richer Claude-GitHub integration |
| Dependabot | Included | 15 min setup, high value |
| Defect sync | Included | Bridges .claude/ tracking to GitHub Issues |
| Release pipeline | Deferred | Focus on quality gates first |
| CLAUDE.md lint note | Included | Each session suggests new lint candidates |
