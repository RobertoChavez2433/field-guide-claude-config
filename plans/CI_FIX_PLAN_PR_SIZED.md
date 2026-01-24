# CI Fix Plan (PR-sized) - Session 88

**Source**: `C:\Users\rseba\.claude\plans\fizzy-sparking-steele.md`

## Goals
- Unblock CI by fixing linting false positives and analyzer failures.
- Keep E2E key linting accurate and resistant to comment noise.
- Keep changes small and reviewable per PR.

---

## PR-1: Harden Hardcoded Key Check (CI)

**Scope**: Fix false positives and expand coverage for `Key("...")`.

**Problems Identified**
- `grep -v "^\s*//"` is not valid in basic `grep` (`\s` is treated as `s`).
- Comment filtering ignores block comments (`/* */`).
- Current regex only matches single quotes and can miss `Key("...")`.

**Change**: `.github/workflows/e2e-tests.yml`

```bash
# Replace current grep pipeline with this
HARDCODED=$(grep -rnE "Key\\(['\"][^'\"]+['\"]\\)" integration_test/patrol/ --include="*.dart" \
  | grep -v "_archived" \
  | grep -v "// allowed:" \
  | grep -v "^[[:space:]]*//" \
  | grep -v "^[[:space:]]*/\\*" \
  | grep -v "^[[:space:]]*\\*" \
  || true)
```

**Notes**
- `^[[:space:]]*//` excludes both `//` and `///`.
- If you want to keep block-comment examples, the two block-comment filters are enough for most cases.

**Verification**
- Ensure CI step fails only when real `Key(...)` usage exists in tests.
- Manually run the command locally to confirm no false positives.

---

## PR-2: Remove Legacy Helpers to Fix Analyzer Errors

**Scope**: Delete unused test helpers that reference `PatrolTester` and break analysis.

**Files to Delete**
- `integration_test/helpers/auth_test_helper.dart`
- `integration_test/helpers/navigation_helper.dart`
- `integration_test/helpers/README.md`

**Notes**
- Active helpers live in `integration_test/patrol/helpers/`.
- If you prefer to keep history, move to `integration_test/helpers/_archived/` and exclude from analysis.

**Verification**
- `flutter analyze` no longer reports `PatrolTester` or `waitUntilVisible` errors.

---

## PR-3: Fix Test Compilation Errors in Mocks and Auth Provider

**Scope**: Resolve mismatched fields and nullable User handling.

**Changes**
- `test/helpers/mocks/mock_repositories.dart`
  - `Contractor.company` -> `c.contactName`
  - `Photo.dailyEntryId` -> `p.entryId`
- `test/features/auth/presentation/providers/auth_provider_test.dart`
  - Only create `Session` when `user != null`

**Verification**
- `flutter analyze`
- `flutter test`

---

## Success Criteria
- CI E2E linting step no longer flags comment-only matches.
- Analyzer passes with 0 errors.
- Unit tests pass without compilation failures.

---

## Suggested Commands
```bash
flutter analyze
flutter test

# Manual lint check
grep -rnE "Key\\(['\"][^'\"]+['\"]\\)" integration_test/patrol/ --include="*.dart" \
  | grep -v "_archived" \
  | grep -v "// allowed:" \
  | grep -v "^[[:space:]]*//" \
  | grep -v "^[[:space:]]*/\\*" \
  | grep -v "^[[:space:]]*\\*"
```
