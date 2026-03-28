# Plan Review: Sync Verification Bugfixes

**Date**: 2026-03-27
**Plan**: `.claude/plans/2026-03-27-sync-verification-bugfixes.md`

## Code Review: REJECT → APPROVED after fixes

### Findings addressed in plan v2:
| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| 1 | CRITICAL | `saveAllCountsForEntry` same sync_control bug | Added Step 1.2.2: delete as dead code |
| 2 | CRITICAL | Integrity checker cleanup too vague | Made Step 4.1.1 specific (line 417 text) |
| 3 | HIGH | SV-1 missing `updated_at` in UPDATE | Added to UPDATE map in Step 2.1.1 |
| 4 | MEDIUM | `companyProjectsCount` badge leak | Added Step 3.1.5 |
| 5 | MEDIUM | Stable ID mismatch for other-contractor equipment | Added to Step 2.3.1 |
| 6 | MEDIUM | `getUsedEquipmentIds` missing deleted_at filter | Added Step 1.3.2 |
| 7 | LOW | No explicit test-writing steps | Noted — tests run in Phase 4 |

### Deferred (not in scope):
- `getTotalCountForEntry` missing deleted_at filter (LOW, cosmetic)
- `archivedProjects` getter unfiltered for inspectors (LOW, separate bug)

## Security Review: APPROVE with 1 HIGH required fix

### Findings addressed in plan v2:
| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| H-1 | HIGH | `saveAllCountsForEntry` retains sync_control | Same as code review #1 |
| M-1 | MEDIUM | `companyProjectsCount` badge leak | Same as code review #4 |
| M-2 | MEDIUM | `getUsedEquipmentIds` missing deleted_at | Same as code review #6 |
| M-3 | MEDIUM | Driver photo EXIF fallback documentation | Plan already logs warning |
| L-1 | LOW | copyWith deletedAt/deletedBy coupling | Documented in plan |
| L-2 | LOW | Deterministic ID format coupling | Documented in plan |

### Security clearances:
- SV-1: No privilege escalation — Supabase RLS WITH CHECK blocks resurrection
- SV-2b/c: Transaction atomicity prevents timing window issues
- SV-4: Client-side filter is defense-in-depth, server RLS already correct
- SV-5: Debug-only scope with kReleaseMode/kProfileMode guards
