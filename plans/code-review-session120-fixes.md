# Code Review Session 120 - Fix Plan (PR-sized)

## Phase 0 - Validation + Scope Check (no code changes)
### Subphase 0.1 - Confirm findings and references
1. Use `rg` to locate all test seed personnel type fixtures.
2. Verify where `displayCode` is used and if any test data could be empty.
3. Confirm current indexes in `database_service.dart` and actual query patterns.

Deliverable: short note of confirmed targets for PR1 and PR2.

---

## PR 1 - Test Seed Data + Helper Alignment
### Subphase 1.1 - Update seed fixtures
1. Update `integration_test/patrol/fixtures/test_seed_data.dart`:
   - Add `contractorId` to every personnel type.
   - Ensure types align with contractor ids used in fixtures.
2. If fixture builder methods exist, update those to require contractorId.

### Subphase 1.2 - Update tests/helpers
1. Update any helper or test that assumes project-scoped personnel types.
2. If keys depend on types, ensure they reference contractor-scoped types.

### Subphase 1.3 - Verification
1. Run `flutter analyze`.
2. Run E2E: `entry_lifecycle_test.dart` + `entry_management_test.dart`.

Deliverable: tests pass with contractor-scoped seed data.

---

## PR 2 - Defensive Model + Minor Readability Improvements
### Subphase 2.1 - Defensive displayCode
1. Update `PersonnelType.displayCode` to handle empty name safely.
2. Keep UI validation as-is.

### Subphase 2.2 - Extract magic number
1. Define a named constant for the `constraints.maxHeight < 200` threshold.
2. Replace hardcoded value in `home_screen.dart`.

### Subphase 2.3 - Verification
1. Run `flutter analyze`.
2. Run a focused widget/unit test pass if available; otherwise note as not run.

Deliverable: safer model + clearer UI constant with no behavior change.

---

## PR 3 - Optional: Index Adjustment (only if needed)
### Subphase 3.1 - Query pattern review
1. Confirm any query that filters by `contractor_id` alone.
2. If none, skip this PR to avoid extra write cost.

### Subphase 3.2 - Add index (conditional)
1. Add `CREATE INDEX IF NOT EXISTS idx_personnel_types_by_contractor ON personnel_types(contractor_id, project_id);`
2. Add to appropriate migration section.

### Subphase 3.3 - Verification
1. Run `flutter analyze`.
2. Run a small DB migration test or local smoke run to ensure migration applies.

Deliverable: index added only if warranted by query patterns.

---

## PR 4 - Optional: Timeout Standardization (test hygiene)
### Subphase 4.1 - Centralize timeouts
1. Add a default timeout constant in `PatrolTestHelpers`.
2. Replace repeated explicit timeouts with the shared constant where appropriate.

### Subphase 4.2 - Verification
1. Run E2E subset to confirm no regressions.

Deliverable: consistent timeout usage across tests.

---

## Notes
- Remove old key references only after `rg` confirms zero usage.
- Keep PRs small and independent; each should leave tests green.
