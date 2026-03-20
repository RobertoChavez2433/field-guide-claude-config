# Plan Review: Test Skill Redesign

**Plan:** `.claude/plans/2026-03-19-test-skill-redesign.md`
**Date:** 2026-03-19

## Code Review Verdict: REJECT → fixed inline

### CRITICAL
1. **`_pumpAndSettle` deadlock** — HTTP server and UI are same isolate. All pump calls must go through `_runWidgetAction`/`scheduleTask`. **FIX: Refactored _pumpAndSettle to use scheduleTask internally.**
2. **Wrong PhotoRepository import** — missing `repositories/` subdirectory. **FIX: Corrected path.**
3. **Proof flow table mismatch** — plan had wrong T01-T14 flows vs spec. **FIX: Replaced with spec-accurate flows.**
4. **(HIGH) `_handleText` `updateEditingValue` won't trigger onChanged** — **FIX: Use controller.text= setter instead.**
5. **(HIGH) `_currentRouteName` always returns null** — **FIX: Use GoRouter.of(context).routerDelegate.currentConfiguration for route name.**
6. **(HIGH) Dispatch group ordering ambiguous** — **FIX: Clarified that Group D runs concurrently with B/C.**

### MEDIUM (addressed)
- TestGesture DRY violation → extracted `_createGesture()` factory
- Temp dir cleanup → TestPhotoService cleanup note added
- build.ps1 verification → use intentionally invalid combo to verify guard
- `date` command Windows → use pwsh Get-Date
- rm paths → use absolute paths
- test_results vs test-results path inconsistency → standardized to `test-results`

## Security Review Verdict: APPROVE WITH CONDITIONS → conditions met

### HIGH
1. **H-01: Auth token via unauthenticated endpoint** — **FIX: Removed GET /driver/token. Agents read from stdout. Token logged truncated to debug server. _postAuthToken removed.**

### MEDIUM (addressed)
- M-01: MOCK_AUTH regex → use `(?m)^\s*MOCK_AUTH\s*=\s*true`
- M-02: Directory.systemTemp → getTemporaryDirectory()
- M-03: Tree PII → redact Text.data in _dumpTree
- M-04: .claude/test-results/ gitignore → added explicitly
- L-01: Token truncated in Logger.lifecycle
- L-03: Body size cap → 15MB inject, 64KB others
