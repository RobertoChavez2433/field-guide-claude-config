# Current Implementation Plan

**Last Updated**: 2026-01-21
**Status**: E2E TEST PLAN - APPROVED WITH CHANGES
**Plan File**: `.claude/implementation/e2e_test_plan.md` (600+ lines)

---

## Overview

**Current Focus**: Consolidate 84 Patrol tests into ~50 E2E journey tests with explicit assertions and structured logging.

**Previous Work Complete**:
- App rename "Construction Inspector" -> "Field Guide"
- Patrol fix Phases 1-5 complete
- Platform update to 2026 standards
- Batched test runner created
- 19/20 individual tests passing (95%)

**Session 44 Complete**: E2E test plan created and code-reviewed (8/10)

---

## Plan Summary

| Metric | Current | Target |
|--------|---------|--------|
| Total tests | 84 | ~50 |
| E2E journey tests | 0 | 33 |
| Isolated tests | 84 | 17 |
| Silent failures | 40% | 0% |
| Structured logging | 0% | 100% |
| Memory crashes | At ~20 | None |
| Runtime | Crashes | 30-40 min |

---

## Pre-Implementation Checklist

From code review (8/10, approved with changes):

- [ ] Widget key audit - verify which keys exist vs need adding
- [ ] Update helper class to remove hardcoded delays
- [ ] Add retry logic to critical operations
- [ ] Implement screenshot capture for failures
- [ ] Verify single test runs before batch execution

---

## Implementation Phases (3-4 weeks)

### Week 1: Foundation & Core Journeys
- [ ] Create `PatrolTestHelpers` class with logging
- [ ] Add Phase 1 widget keys to 6 UI files
- [ ] Implement Journey 1: Entry lifecycle (3 tests)
- [ ] Implement Journey 4: Project management (2 tests)
- [ ] Run Batches 1-2

### Week 2: Additional Journeys & Isolated Tests
- [ ] Implement Journey 2: Offline/sync (2 tests)
- [ ] Implement Journey 5: Photo flow (2 tests)
- [ ] Migrate permission tests (6 tests)
- [ ] Migrate validation tests (5 tests)
- [ ] Run Batches 3-6

### Week 3-4: Cleanup & Validation
- [ ] Delete/archive old test files
- [ ] Full regression (all 9 batches)
- [ ] Fix flaky tests
- [ ] Documentation update

---

## Test Batches

| Batch | Tests | Type | Duration |
|-------|-------|------|----------|
| 1 | Entry lifecycle (5) | E2E | ~3 min |
| 2 | Project & Settings (4) | E2E | ~2 min |
| 3 | Offline & Photos (4) | E2E | ~3 min |
| 4 | Navigation E2E (3) | E2E | ~2 min |
| 5 | Camera permissions (3) | Isolated | ~2 min |
| 6 | Location & Validation (5) | Isolated | ~2 min |
| 7 | Auth & Nav edge (5) | Isolated | ~2 min |
| 8 | App lifecycle (4) | Isolated | ~3 min |
| 9 | Smoke tests (3) | E2E | ~2 min |

---

## Related Files

- Full E2E plan: `.claude/implementation/e2e_test_plan.md`
- Session state: `.claude/plans/_state.md`
- Latest session: `.claude/docs/latest-session.md`
- Defect log: `.claude/memory/defects.md`

---

**Last Updated**: 2026-01-21
**Session**: 44
