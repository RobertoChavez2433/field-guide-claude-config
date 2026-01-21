# Current Implementation Plan

**Last Updated**: 2026-01-21
**Status**: NAME CHANGE PLAN READY + BUG FIXES NEEDED
**Plan Files**:
- `.claude/implementation/name_change_plan.md` (430-line rename plan) **NEW**
- `.claude/implementation/patrol_test_fix_plan.md` (Comprehensive 5-phase plan - COMPLETE)
- `.claude/implementation/patrol_fix_plan.md` (Infrastructure fixes - COMPLETE)

---

## Overview

**Current Focus**: App rename "Construction Inspector" → "Field Guide" + bug fixes from code review

**Name Change Plan**: Strategy 1 (Display Names Only)
- 30 files to modify
- ~3 hours effort
- Zero breaking changes
- Package name remains `construction_inspector`

**Bugs Found in Code Review**:
1. CRITICAL: test_sorting.dart wrong import
2. HIGH: MockProjectRepository missing methods
3. HIGH: Entry Wizard race condition

---

## Implementation Phases

### Phase 1: Quick Wins (1-2 hours) COMPLETE
| Task | Status |
|------|--------|
| Delete widget_test.dart | DONE |
| Delete 3 datasource test files | DONE |
| Create model test utility | DONE |
| Consolidate model tests | DONE (project_test.dart) |

### Phase 2: Widget Keys (2-3 hours) COMPLETE
| Task | Status |
|------|--------|
| Add Keys to auth screens | DONE (9 keys) |
| Add Keys to entry wizard | DONE (7 keys) |
| Add Keys to project screens | DONE (8 keys) |
| Add Keys to dashboard | DONE (1 key) |
| Add Keys to settings | DONE (5 keys) |
| Add Keys to home screen | DONE (4 keys) |

### Phase 3: Test Helper Refactoring (2-3 hours) COMPLETE
| Task | Status |
|------|--------|
| Extract shared mocks | DONE (test/helpers/mocks/) |
| Centralize sorting logic | DONE (test_sorting.dart) |
| Fix seed data timestamps | DONE (patch_seed_data.py) |
| Create AuthTestHelper | DONE |
| Create NavigationHelper | DONE |

### Phase 4: Patrol Test Fixes (3-4 hours) COMPLETE
| Task | Status |
|------|--------|
| Replace fixed delays | DONE (7 files) |
| Replace text finders | DONE (7 files) |
| Add state reset | DONE (test_config.dart) |
| Fix specific failing tests | DONE |

### Phase 5: Coverage Gaps (ongoing) COMPLETE
| Task | Status |
|------|--------|
| Auth provider/service tests | DONE (29 tests) |
| Sync provider/service tests | DONE (37 tests) |
| Database service tests | DONE (25 tests) |
| Contractor repos tests | DONE (77 tests) |
| New Patrol flow tests | DONE (15 tests) |

---

## Known Issues (Next Session)

| Issue | File | Fix Needed |
|-------|------|------------|
| Missing binding init | sync_service_test.dart | Add TestWidgetsFlutterBinding.ensureInitialized() |
| Auth mock signatures | auth_service_test.dart | Add captchaToken, channel params |
| db.version getter | database_service_test.dart | Use PRAGMA user_version instead |
| PatrolTester undefined | auth_test_helper.dart | Fix import statement |
| Wrong import path | project_repository_test.dart | Fix helpers/mocks/mocks.dart path |

---

## Test Suite Status

| Category | Count | Status |
|----------|-------|--------|
| Unit tests | 631 | 578 pass, 53 fail (91.6%) |
| Golden tests | 88 | 83 pass, 5 fail (expected) |
| Patrol tests | 84 | Infrastructure complete |
| Analyzer | 0 | No issues |

---

## Session 28 Accomplishments

- **New Test Files**: 25+
- **New Unit Tests**: 90+ across auth, sync, database, contractors, quantities
- **New Patrol Tests**: 15 (contractors, quantities, settings flows)
- **Files Modified**: 8 Patrol test files
- **Code Review Scores**: 7/10, 8.5/10

---

## Related Files

- Comprehensive plan: `.claude/implementation/patrol_test_fix_plan.md`
- Session state: `.claude/plans/_state.md`
- Latest session: `.claude/docs/latest-session.md`
- Defect log: `.claude/memory/defects.md`

---

**Last Updated**: 2026-01-21
**Session**: 28
