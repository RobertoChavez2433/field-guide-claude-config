# Analyzer Cleanup Plan v2

**Created**: 2026-02-01
**Status**: READY FOR IMPLEMENTATION
**Scope**: Analyzer fixes (v1 Phases 1-6) + codebase hygiene (docs, paths, logs, legacy artifacts)

## Overview

This v2 plan keeps the analyzer cleanup phases from v1 and adds targeted hygiene work after reviewing the codebase. The new phases focus on outdated paths in docs, Patrol config/documentation drift, legacy test artifacts, and accumulated local logs/outputs that obscure signal during debugging.

## Gaps & Hygiene Findings (from codebase review)

- **Outdated Patrol docs and paths** in `integration_test/patrol/README.md` (mentions `test_bundle.dart`, Patrol v3.20.0, and missing `/e2e_tests/` paths; the current `integration_test/patrol/e2e_tests/` directory has 15 files, not 11). (`integration_test/patrol/README.md`)
- **Patrol config drift**: `patrol.yaml` targets `integration_test/test_bundle.dart` while the project now uses `patrol:` config in `pubspec.yaml` and v4 tooling. (`patrol.yaml`, `pubspec.yaml`)
- **Legacy integration_test driver** still present and unreferenced. (`test_driver/integration_test.dart`)
- **Accumulated local logs/outputs in repo root** (flutter_*.log, e2e_*.log, analyze_*.txt, test_*.txt, `nul`). These are already ignored, but clutter the workspace and can hide relevant artifacts. (`flutter_01.log` … `flutter_13.log`, `e2e_latest.log`, `analyze_output.txt`, `analyzer_output.txt`, `test_result.txt`, `nul`, etc.)
- **Root-level scripts and utilities** that could be relocated under `scripts/` or `tooling/` to reduce top-level noise. (`run_patrol.ps1`, `run_patrol_debug.ps1`, `verify_deep_linking.bat`, `verify_deep_linking.sh`, `patch_seed_data.py`, `update_seed_data.py`)
- **Node tooling is present but local-only** and ignored; decide whether to keep in root or move under a dedicated tooling folder. (`package.json`, `package-lock.json`, `node_modules/`)

---

## Phase 1: CRITICAL - Fix test_bundle.dart (BLOCKING)

**Priority**: CRITICAL
**Issues**: 7 errors (v1)
**Agent**: `qa-testing-agent`

### Summary
Fix `integration_test/test_bundle.dart` for Patrol v4 to unblock test execution.

### Changes Required
**File**: `integration_test/test_bundle.dart`

| Line | Issue | Fix |
|------|-------|-----|
| 8 | Importing internal API | Remove `package:patrol/src/native/contracts/contracts.dart` |
| 62 | NativeAutomator deprecated | Replace with `PlatformAutomator()` |
| 62-64 | Missing platformAutomator arg | Pass `platformAutomator` to `PatrolBinding.ensureInitialized()` |
| 63 | initialize() undefined | Remove `await nativeAutomator.initialize();` |
| 111 | markPatrolAppServiceReady undefined | Remove call |

### Verification
```bash
pwsh -Command "flutter analyze integration_test/test_bundle.dart"
```

---

## Phase 2: Quick Wins - Unused/Duplicate Imports

**Priority**: HIGH
**Issues**: 30 warnings (v1)
**Agent**: `code-review-agent`

### Summary
Remove unused/duplicate imports in `integration_test/`, `lib/`, and `test/`.

### Changes Required (same as v1)
- `integration_test/patrol/e2e_tests/*.dart`
- `integration_test/patrol/helpers/patrol_test_helpers.dart`
- `integration_test/patrol/isolated/*.dart`
- `lib/features/pdf/presentation/screens/measurement_spec_preview_screen.dart`
- `lib/features/quantities/presentation/screens/quantities_screen.dart`
- `lib/features/settings/presentation/screens/settings_screen.dart`
- `lib/features/settings/presentation/widgets/*.dart`
- `test/features/toolbox/services/auto_fill_context_builder_test.dart`
- `test/helpers/mocks/mock_services.dart`

### Verification
```bash
pwsh -Command "flutter analyze"
```

---

## Phase 3: Deprecated Flutter APIs

**Priority**: HIGH
**Issues**: 10 info/warn (v1)
**Agent**: `flutter-specialist-agent`

### Summary
Replace deprecated APIs across UI and form widgets.

### Key Files
- `lib/features/projects/presentation/screens/project_setup_screen.dart` (WillPopScope → PopScope)
- `lib/features/toolbox/presentation/widgets/dynamic_form_field.dart` (RadioGroup + withValues + FormField.initialValue)
- `lib/features/toolbox/presentation/screens/gallery_screen.dart` (initialValue)
- `lib/features/toolbox/presentation/widgets/form_preview_tab.dart` (withValues)

### Verification
```bash
pwsh -Command "flutter analyze --no-fatal-infos | Select-String 'deprecated_member_use'"
```

---

## Phase 4: Async Context Safety

**Priority**: MEDIUM
**Issues**: 15 info (v1)
**Agent**: `flutter-specialist-agent`

### Key Files
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

### Verification
```bash
pwsh -Command "flutter analyze --no-fatal-infos | Select-String 'use_build_context_synchronously'"
```

---

## Phase 5: Code Cleanup - Unused Vars & Missing @override

**Priority**: MEDIUM
**Issues**: 33 (v1)
**Agent**: `code-review-agent`

### Key Files
- `integration_test/patrol/e2e_tests/toolbox_flow_test.dart`
- `integration_test/patrol/isolated/app_lifecycle_test.dart`
- `test/features/toolbox/presentation/screens/forms_list_screen_test.dart`
- `test/services/sync_service_test.dart`
- `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`
- `lib/services/sync_service.dart`
- `lib/features/*/data/repositories/*.dart`
- `lib/features/pdf/presentation/widgets/import_type_dialog.dart`

### Verification
```bash
pwsh -Command "flutter analyze --no-fatal-infos | Select-String -Pattern 'unused_local_variable|unused_field|annotate_overrides|overridden_fields|dead_code'"
```

---

## Phase 6: Test Code Cleanup

**Priority**: LOW
**Issues**: 64 (v1)
**Agent**: `qa-testing-agent`

### Key Files
- `integration_test/patrol/e2e_tests/offline_sync_test.dart`
- `integration_test/patrol/e2e_tests/photo_flow_test.dart`
- `integration_test/patrol/e2e_tests/project_management_test.dart`
- `integration_test/patrol/helpers/patrol_test_helpers.dart`
- `test/features/**/screens/*_test.dart`
- `integration_test/patrol/test_config.dart`
- `lib/core/config/test_mode_config.dart`
- `lib/features/toolbox/presentation/widgets/weight_20_10_section.dart`
- `lib/shared/utils/validators.dart`
- `test/helpers/mocks/mocks.dart`
- `test/golden/test_helpers.dart`

### Verification
```bash
pwsh -Command "flutter analyze --no-fatal-infos | Select-String -Pattern 'await_only_futures|unnecessary_null_comparison|prefer_function_declarations|avoid_print|camel_case_types|dangling_library_doc|use_super_parameters'"
```

---

## Phase 7: Patrol Config & Documentation Alignment

**Priority**: HIGH
**Goal**: Remove outdated paths and sync docs with Patrol v4 configuration.

### 7.1 Update Patrol README (doc drift + paths)
**File**: `integration_test/patrol/README.md`

- Update **Run All Tests** section to reflect v4 discovery (no `test_bundle.dart` claim).
- Fix **Run Specific Test File** paths to include `integration_test/patrol/e2e_tests/…`.
- Refresh **Test Statistics** to reflect actual file counts from `integration_test/patrol/e2e_tests/` and `integration_test/patrol/isolated/`.
- Update **Patrol Version** to match `pubspec.yaml` (`patrol: ^4.1.0`).

### 7.2 Align Patrol config sources
**Files**: `patrol.yaml`, `pubspec.yaml`

- Decide whether to keep **both** configs or consolidate into one.
- If keeping `patrol.yaml`, update `targets` away from `integration_test/test_bundle.dart` (use `integration_test` or explicit test list).
- If consolidating into `pubspec.yaml`, remove redundant items from `patrol.yaml` and reference `pubspec.yaml` in docs.

### Verification
```bash
patrol --version
patrol test --help
```

---

## Phase 8: Legacy Integration Test Artifacts

**Priority**: MEDIUM
**Goal**: Remove unused legacy driver file and keep only Patrol-based test flow.

### 8.1 Remove Flutter driver stub
**File**: `test_driver/integration_test.dart`

- Confirm no references (currently only file in `test_driver/`).
- Remove folder if Patrol is the sole integration test runner.

### Verification
```bash
rg -n "test_driver"
```

---

## Phase 9: Root Workspace Hygiene (logs + outputs)

**Priority**: MEDIUM
**Goal**: Reduce root clutter and standardize log/output storage.

### 9.1 Remove or archive root logs
**Files**:
- `flutter_01.log` … `flutter_13.log`
- `e2e_batch1.log`
- `e2e_entry_management_verbose.log`
- `e2e_latest.log`
- `e2e_test_results.log`
- `analyze_output.txt`
- `analyze_result.txt`
- `analyzer_output.txt`
- `test_output.txt`
- `test_result.txt`
- `sync_test_output.txt`
- `nul`

### 9.2 Relocate future outputs
- Move ad-hoc test/debug outputs under `.claude/outputs/` or `tooling/outputs/`.
- Update any scripts that emit output to use a consistent output directory.

---

## Phase 10: Script & Utility Consolidation

**Priority**: LOW
**Goal**: Keep root clean and reduce path drift.

### 10.1 Move standalone scripts
**Files**:
- `run_patrol.ps1`
- `run_patrol_debug.ps1`
- `verify_deep_linking.bat`
- `verify_deep_linking.sh`
- `patch_seed_data.py`
- `update_seed_data.py`

**Target**: `scripts/` or `tooling/` (pick one, update README if necessary).

### 10.2 Update any references
- Search for script names in docs and update paths accordingly.

---

## Phase 11: Node Tooling Decision

**Priority**: LOW
**Goal**: Make JS tooling intentional and discoverable.

### Options
1. **Keep in root** (document in README and explain it’s for Supabase tooling).
2. **Move under `tooling/supabase/`** and update any scripts/docs.
3. **Remove entirely** if no longer used, and rely on global Supabase CLI.

**Files**:
- `package.json`
- `package-lock.json`
- `node_modules/`

---

## Execution Order

| Phase | Priority | Goal | Estimated Time |
|------|----------|------|----------------|
| 1-6 | HIGH → LOW | Analyzer cleanup (v1) | 2–3 hours |
| 7 | HIGH | Patrol config/docs alignment | 30–45 min |
| 8 | MEDIUM | Legacy test artifacts | 10 min |
| 9 | MEDIUM | Root log cleanup | 10–20 min |
| 10 | LOW | Script consolidation | 20–30 min |
| 11 | LOW | Node tooling decision | 10–20 min |

## Success Criteria

- `flutter analyze` returns **0 issues**.
- `integration_test/patrol/README.md` reflects Patrol v4 paths and current test count.
- No stale `test_bundle.dart` references in docs or configs (unless explicitly required).
- Workspace root contains **no transient logs**; outputs moved under `.claude/outputs/` or `tooling/outputs/`.

## Notes

- If you still need `test_bundle.dart` generation, keep it but **remove references in docs** and update `patrol.yaml` accordingly.
- If moving scripts, update any path references in docs or CI.
- Keep `.gitignore` as-is; it already excludes most artifacts, but cleaning the workspace improves signal during debugging.
