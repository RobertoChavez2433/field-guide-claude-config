---
name: context-memory-optimization-v2
description: Align docs/agents/standards/tech-stack with current codebase and fix Claude context references
status: COMPLETE
created: 2026-02-01
completed: 2026-02-01
priority: HIGH
---

# Context + Documentation Alignment Plan (v2)

## Objectives
- Ensure Claude docs, agent files, standards, and tech-stack reflect the current codebase.
- Fix broken references, missing files, and stale paths.
- Keep memory/context usage efficient and intentional.

---

## Phase 1: Inventory & Baseline

### 1.1 Project Structure Snapshot
- Capture actual feature list from lib/features/ (includes 	oolbox).
- Record actual service locations:
  - lib/features/pdf/services/pdf_service.dart
  - lib/services/sync_service.dart
  - lib/core/database/ + lib/core/database/schema/
- Confirm empty legacy folders:
  - lib/data/ and lib/presentation/ are empty (no barrels).

### 1.2 Platform/Tooling Snapshot
- Android versions from ndroid/app/build.gradle.kts:
  - compileSdk 36, targetSdk 36, minSdk 24
  - Orchestrator 1.6.1
- Gradle version from ndroid/gradle/wrapper/gradle-wrapper.properties:
  - 8.14
- iOS deployment target from ios/Runner.xcodeproj/project.pbxproj:
  - 15.0
- Patrol version from pubspec.yaml: 4.1.0

### 1.3 Claude Reference Integrity
- Enumerate all @ references in .claude/**.md and mark missing paths:
  - @.claude/memory/state-archive.md (missing)
  - @.claude/memory/defects-archive.md (wrong filename)
  - .claude/logs/session-log.md referenced but missing

---

## Phase 2: Update Core Docs

### 2.1 Update .claude/CLAUDE.md
- Add 	oolbox to features list.
- Fix key file paths:
  - lib/features/pdf/services/pdf_service.dart
  - lib/services/sync_service.dart
- Remove references to empty legacy barrels or mark as deprecated explicitly.
- Keep Quick Reference accurate (ensure @ links point to real files).

### 2.2 Update .claude/docs/architectural_patterns.md
- Change “12 features” to 13 (include 	oolbox).
- Update structure narrative to reflect:
  - lib/core/database/schema/ usage
  - No domain/ layer in feature modules
- Verify references to sample files still exist.

### 2.3 Update .claude/docs/2026-platform-standards-update.md
- Align to current config:
  - compileSdk/targetSdk 36
  - Orchestrator 1.6.1
  - Patrol 4.1.0
- Ensure test config table matches actual versions.

---

## Phase 3: Update Standards & Rules

### 3.1 .claude/memory/standards.md
- Replace “data/domain/presentation” with actual data/presentation layout.
- Remove FutureProvider guidance if not used in code.
- Align testing pyramid with QA agent (choose 70/20/10 or update QA to 60/20/20).

### 3.2 .claude/rules/frontend/flutter-ui.md
- Update paths: to lib/features/**/presentation/** (and keep core theme/router).
- Replace examples that reference lib/presentation/ only.

### 3.3 .claude/rules/backend/data-layer.md
- Update paths: to include lib/features/**/data/** and lib/core/database/**.
- Fix schema version reference and remove outdated lib/services/database_service.dart path.

### 3.4 .claude/rules/quality-checklist.md
- Replace “data/domain/presentation” with actual layout.

---

## Phase 4: Update Agent Files

### 4.1 data-layer-agent.md
- Replace legacy paths (lib/data/*, lib/services/database_service.dart).
- Update table list to match current schema (include toolbox tables).
- Remove “Remaining Work” entries that are now complete.

### 4.2 lutter-specialist-agent.md
- Update responsibilities and file paths to use lib/features/**/presentation/**.

### 4.3 qa-testing-agent.md
- Update TestingKeys path to lib/shared/testing_keys/testing_keys.dart.
- Ensure testing pyramid aligns with standards.

### 4.4 pdf-agent.md
- Update main PDF service path to lib/features/pdf/services/pdf_service.dart.

---

## Phase 5: Fix Memory/Archive References

### 5.1 Archives & Logs
- Standard: Use hyphen naming (defects-archive.md, state-archive.md).
- state-archive.md already created.
- session-log.md already created.

### 5.2 Commands
- Update /resume-session and /end-session to reference the correct archive filenames.
- Optional: clarify “hot vs cold memory” and avoid eager @ imports in CLAUDE.md.

---

## Phase 6: Verification - COMPLETE

### 6.1 @ Reference Check - PASSED
All @ references now resolve to existing files:
- @.claude/memory/tech-stack.md ✓
- @.claude/memory/standards.md ✓
- @.claude/memory/defects.md ✓
- @.claude/memory/state-archive.md ✓
- @.claude/memory/defects-archive.md ✓
- @.claude/rules/frontend/ ✓ (contains flutter-ui.md)
- @.claude/rules/backend/ ✓ (contains data-layer.md)
- @.claude/rules/auth/ ✓ (contains supabase-auth.md)
- @.claude/rules/coding-standards.md ✓
- @.claude/rules/defect-logging.md ✓
- @.claude/rules/quality-checklist.md ✓
- @.claude/docs/architectural_patterns.md ✓
- @.claude/docs/testing-guide.md ✓
- @.claude/docs/pdf-workflows.md ✓
- @.claude/docs/sql-cookbook.md ✓
- @.claude/docs/e2e-test-setup.md ✓
- @.claude/logs/session-log.md ✓

**Fixed**: defects.md reference updated from non-existent `@.claude/plans/e2e-testing-remediation-plan.md` to `@.claude/docs/e2e-test-setup.md`

### 6.2 Feature Count - CONSISTENT
| Document | Count | Status |
|----------|-------|--------|
| CLAUDE.md | 13 | ✓ |
| architectural_patterns.md | 13 | ✓ |
| data-layer-agent.md | Lists all features | ✓ |

Actual features in lib/features/: auth, contractors, dashboard, entries, locations, pdf, photos, projects, quantities, settings, sync, toolbox, weather (13 total)

### 6.3 File Paths - CONSISTENT
| File | CLAUDE.md | Other Docs | Status |
|------|-----------|------------|--------|
| Database | lib/core/database/database_service.dart | Same | ✓ |
| Router | lib/core/router/app_router.dart | Same | ✓ |
| TestingKeys | lib/shared/testing_keys/testing_keys.dart | Same | ✓ |

**Fixed**: defects.md TestingKeys path updated to full path `lib/shared/testing_keys/testing_keys.dart`

### 6.4 Testing Strategy - ALIGNED
| Document | Unit | Widget | Integration |
|----------|------|--------|-------------|
| standards.md | 60% | 20% | 20% |
| qa-testing-agent.md | 60% | 20% | 20% |

### 6.5 Platform Versions - ALIGNED
| Component | CLAUDE.md | 2026-platform-standards.md | Status |
|-----------|-----------|---------------------------|--------|
| compileSdk | 36 | 36 | ✓ |
| targetSdk | 36 | 36 | ✓ |
| minSdk | 24 | 24 | ✓ |
| Gradle | 8.14 | 8.14 | ✓ |
| Kotlin | 2.2.20 | 2.2.20 | ✓ |
| iOS Min | 15.0 | 15.0 | ✓ |
| Patrol | 4.1.0 | 4.1.0 | ✓ |
| Orchestrator | 1.6.1 | 1.6.1 | ✓ |

---

## Deliverables
- Updated .claude/CLAUDE.md, .claude/docs/*, .claude/memory/*, .claude/rules/*, and agent files.
- Added missing archive/log files or reconciled naming.
- All references consistent and accurate.
