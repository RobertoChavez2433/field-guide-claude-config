# Current Implementation Plan

**Last Updated**: 2026-01-21
**Status**: READY FOR IMPLEMENTATION
**Plan Files**:
- `.claude/implementation/patrol_test_fix_plan.md` (Comprehensive 5-phase plan - NEW)
- `.claude/implementation/patrol_fix_plan.md` (Infrastructure fixes - COMPLETE)

---

## Overview

**Previous Issue**: Patrol tests execute but only 3/69 pass
**Root Causes Identified** (Session 26):
1. Only 28 Key widgets (need 100+ for reliable testing)
2. Text-based finders instead of Key-based finders
3. Fixed delays instead of waitUntilVisible
4. No test state reset between tests
5. ~4,400 lines of redundant tests
6. 61 missing test files

**Current State**: Comprehensive fix plan ready for implementation

---

## Implementation Phases

### Phase 1: Quick Wins (1-2 hours)
| Task | Status |
|------|--------|
| Delete widget_test.dart | PENDING |
| Delete 3 datasource test files | PENDING |
| Create model test utility | PENDING |
| Consolidate model tests | PENDING |

### Phase 2: Widget Keys (2-3 hours)
| Task | Status |
|------|--------|
| Add Keys to auth screens | PENDING |
| Add Keys to entry wizard | PENDING |
| Add Keys to project screens | PENDING |
| Add Keys to dashboard | PENDING |
| Add Keys to settings | PENDING |

### Phase 3: Test Helper Refactoring (2-3 hours)
| Task | Status |
|------|--------|
| Extract shared mocks | PENDING |
| Centralize sorting logic | PENDING |
| Fix seed data timestamps | PENDING |
| Create AuthTestHelper | PENDING |
| Create NavigationHelper | PENDING |

### Phase 4: Patrol Test Fixes (3-4 hours)
| Task | Status |
|------|--------|
| Replace fixed delays | PENDING |
| Replace text finders | PENDING |
| Add state reset | PENDING |
| Fix specific failing tests | PENDING |

### Phase 5: Coverage Gaps (ongoing)
| Task | Priority |
|------|----------|
| Auth provider/service tests | CRITICAL |
| Sync provider/service tests | CRITICAL |
| Database service tests | CRITICAL |
| Contractor repos tests | HIGH |
| New Patrol flow tests | MEDIUM |

---

## Test Suite Status

| Category | Count | Status |
|----------|-------|--------|
| Unit tests | 613 | Passing |
| Golden tests | 93 | Passing |
| Patrol tests | 69 | 3 pass, ~13 fail |
| Analyzer | 0 | No issues |

---

## Related Files

- Comprehensive plan: `.claude/implementation/patrol_test_fix_plan.md`
- Session state: `.claude/plans/_state.md`
- Latest session: `.claude/docs/latest-session.md`
- Defect log: `.claude/memory/defects.md`

---

**Last Updated**: 2026-01-21
**Session**: 26
