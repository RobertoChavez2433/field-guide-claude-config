# Current Implementation Plan

**Last Updated**: 2026-01-21
**Status**: PATROL FIX PHASES 1 & 2 COMPLETE
**Plan Files**:
- `.claude/implementation/patrol_test_fix_plan_v2.md` (579-line comprehensive plan)
- `.claude/implementation/name_change_plan.md` (430-line rename plan) **EXECUTED**
- `.claude/implementation/patrol_test_fix_plan.md` (Original 5-phase plan - superseded)

---

## Overview

**Completed**:
- App rename "Construction Inspector" → "Field Guide" (20 files)
- Patrol fix Phase 1: Quick wins (test file fixes)
- Patrol fix Phase 2: Screen Key additions

**Next Focus**: Execute Phases 3-5 (test patterns, infrastructure, verification)

**Patrol Test Status**: PHASES 1 & 2 COMPLETE
- 10 tests expected to pass (up from 3)
- Phase 3-5 to reach 95% pass rate

---

## Patrol Test Fix Phases

### Phase 1: Quick Wins (1-2 hours) COMPLETE
| Task | Status | Tests Fixed |
|------|--------|-------------|
| Fix icon mismatch (visibility_outlined) | DONE | Test 6 |
| Fix Key name (register_back_to_login_button) | DONE | Test 7 |
| Add missing error assertion | DONE (already present) | Test 3 |
**Agent**: `qa-testing-agent`

### Phase 2: Screen Key Additions (2-3 hours) COMPLETE
| Task | Status | Tests Fixed |
|------|--------|-------------|
| Add Key to RegisterScreen AppBar | DONE | Tests 4, 5, 8, 9 |
| Add Key to ForgotPasswordScreen AppBar | DONE | Tests 4, 5 |
| Add Key('photo_capture_camera') | DONE | Camera 1, 2, 3 |
| Add Keys to ProjectSetup TabBar | DONE | Contractors 1-4 |
**Agent**: `flutter-specialist-agent`

### Phase 3: Test Pattern Improvements (2-3 hours) READY
| Task | Status | Tests Fixed |
|------|--------|-------------|
| Replace text selectors with Key selectors | READY | Tests 5, 8 |
| Remove conditional if-exists masking | READY | Tests 6, 7, 9 |
**Agent**: `qa-testing-agent`

### Phase 4: Infrastructure Improvements (3-4 hours) READY
| Task | Status | Tests Fixed |
|------|--------|-------------|
| Increase camera timeouts (10s → 20s) | READY | Camera 1, 2, 3 |
| Add contractor dialog Keys | READY | Contractors 1, 3 |
| Replace swipe with menu tap | READY | Contractors 4 |
| Add memory cleanup tearDown | READY | All |
**Agent**: `qa-testing-agent`

### Phase 5: Verification (1 hour) READY
| Task | Status |
|------|--------|
| Run full Patrol test suite | READY |
| Verify 95% pass rate | READY |
| Update documentation | READY |
**Agent**: `qa-testing-agent`

---

## Expected Results by Phase

| Phase | Tests Fixed | Cumulative Pass Rate |
|-------|-------------|----------------------|
| Start | 0 | 3/20 (15%) |
| Phase 1 | 3 | 6/20 (30%) |
| Phase 2 | 7 | 13/20 (65%) |
| Phase 3 | 2 | 15/20 (75%) |
| Phase 4 | 4 | 19/20 (95%) |

**Current Status**: Phases 1 & 2 complete. Expected 10/20 (50%) passing.

---

## Test Suite Status

| Category | Count | Status |
|----------|-------|--------|
| Unit tests | 363 | Passing |
| Golden tests | 29 | Passing |
| Patrol tests | 20 | 3 pass, 17 fail (fix plan ready) |
| Analyzer | 0 | No errors |

---

## Completed This Session

### Name Change (Session 31)
- **Files Modified**: 20
- **Platforms**: Android, iOS, Windows, Web, Dart
- **Status**: COMPLETE

### Patrol Investigation (Session 31)
- **Failures Analyzed**: 17
- **Root Causes Identified**: 6 categories
- **QA Confidence**: 95%
- **Status**: COMPLETE

---

## Related Files

- Patrol fix plan v2: `.claude/implementation/patrol_test_fix_plan_v2.md`
- Name change plan: `.claude/implementation/name_change_plan.md`
- Session state: `.claude/plans/_state.md`
- Latest session: `.claude/docs/latest-session.md`
- Defect log: `.claude/memory/defects.md`

---

**Last Updated**: 2026-01-21
**Session**: 31
