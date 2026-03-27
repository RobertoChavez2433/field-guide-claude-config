# Delete Flow Fix Plan Review — 2026-03-26

## Code Review: APPROVE WITH CONDITIONS

### CRITICAL (Fixed)
1. `isInspector` getter missing on AuthProvider — made a firm step (not conditional)

### HIGH (Fixed)
1. Added `project_assignments` to cascade trigger (has deleted_at/deleted_by columns)
2. Documented `stamp_deleted_by` auth.uid() NULL constraint in trigger comments
3. Removed reference to non-existent test file in Phase 4C

### MEDIUM (Noted)
1. No screen-level role gating test — noted for implementation
2. removeFromDevice test should also verify fetchRemoteProjects reappearance — noted

### LOW
1. Barrel export ordering (cosmetic)
2. Step renumbering is brittle (use code content matching, not line numbers)

## Security Review: CONDITIONAL APPROVE

### HIGH→MEDIUM (Mitigated)
1. Offline delete gap — `isOffline` guard on ProjectDeleteSheet disables database delete checkbox when offline. Documented as safety net.

### MEDIUM (Fixed)
1. SEC-M3: Added `refreshUserProfile()` before TOCTOU re-check in `_confirmAndDeleteFromDatabase`

### MEDIUM (Documented)
1. SEC-M1: SECURITY DEFINER cascade bypasses RLS — intentional, FK integrity is safety net
2. SEC-M2: `stamp_deleted_by` EXCEPTION on NULL auth.uid() — documented constraint (authenticated sessions only)

### LOW (Accepted)
1. RAISE LOG exposes project UUIDs — consistent with existing RPC logging
2. Preserved project metadata after removal — minimal, not PII

## Fixes Applied to Plan (Sweep 1 → 2)
- `isInspector` is now a firm step 3D.2
- `project_assignments` added to cascade trigger
- `refreshUserProfile()` added before TOCTOU re-check
- Phase 4C changed from non-existent file to `flutter test test/features/projects/`
- Added auth.uid() constraint documentation in trigger comments
- removeFromDevice test now verifies reappearance via fetchRemoteProjects query
- Added role-gating tests, auto-check behavior test, remove-only path test
- Replaced tautological role-gating test with deferred-to-e2e note

## Sweep 2 Results
- **Code Review**: APPROVE — all 7 fixes verified, ground truth passes
- **Security Review**: APPROVE — all 3 security fixes verified
- Both flagged vacuous test → fixed (replaced with note)
- Implementing agent should verify `stamp_deleted_by` trigger exists on `inspector_forms`
