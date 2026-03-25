# Plan Review: Sync & Data Integrity Verification

**Date:** 2026-03-25
**Plan:** `.claude/plans/2026-03-25-sync-data-integrity-verification.md`

## Code Review: REJECT (3 CRITICAL, 5 HIGH, 4 MEDIUM)

### CRITICAL
1. **Location.copyWith nullability** — `copyWith(description: null)` keeps existing value; can't clear description. Same for Equipment.
2. **Sweep misses child tables** — `sweepVrfRecords` only hits 7 named tables, misses daily_entries, entry_* junction tables, photos, form_responses, calculation_history. Orphans persist after failed runs.
3. **PDF verification is no-op** — `pdf-parse` reads text content, not AcroForm fields. `|| true` fallbacks silently pass.

### HIGH
4. **F2 weather dropdown not opened** — taps `weather_condition_sunny` without opening dropdown first
5. **personnel_types cascade** — may be company-scoped not project-scoped; verify before including in cascade check
6. **F1 post-save navigation** — after project save, app may navigate away; need explicit nav back to edit screen
7. **F2 wizard vs report screen** — plan mixes wizard keys and report keys without showing transition
8. **DatabaseService provider** — verify available above ProjectListScreen (likely app-wide, but confirm)

### MEDIUM
9. **Duplicate sweep logic** — scenario-helpers.js and supabase-verifier.js both implement sweepVrfRecords
10. **Premature L2/L3 deletion** — move to deprecated/ first, delete after integrity suite passes
11. **No --dry-run flag parsing** in run-tests.js
12. **entry_contractors FK query** — uses project_id but may need entry_id chain

### MISSING REQUIREMENTS (from spec)
- Photo update step (description → "VRF-Updated trench photo")
- Entry equipment update step (toggle different item)
- Personnel count increment step (laborer count)
- Form response remarks update (append "VRF-Retest required")
- Both PDFs in same output folder verification
- Local orphan sweep on both devices

## Security Review: APPROVE with conditions

### Required before merge
- SEC-002: Add length cap on `deleted_by_name` rendering (60 chars)
- SEC-004: Add `.env.test` (no glob) to `.gitignore`

### Tracked (not blocking)
- SEC-001: Orphan sweep gap documentation
- SEC-005: Verify RLS write policies on locations/equipment
- SEC-006: Verify deleteCalculation RLS restricts to owner/admin
