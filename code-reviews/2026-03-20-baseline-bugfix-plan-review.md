# Plan Review: 2026-03-20-baseline-bugfix

## Reviewers
- **Code Review Agent**: REJECT → fixed
- **Security Agent**: APPROVE WITH CONDITIONS → conditions addressed

## Findings Addressed (all fixed in plan v2)

### CRITICAL (3) — All Fixed
1. **Bug 7 migration**: `profiles` → `user_profiles`, `user_id` → `id`, added backfill SQL
2. **Bug 2 v39 migration**: Rewrote to use `change_log` table (actual error tracking), scoped to 22P02 errors
3. **Bug 1 `_currentUserId`**: Replaced with `userId` (actual field name on SyncEngine)

### HIGH (6) — All Fixed
4. **Bug 7 backfill**: Added UPDATE...FROM auth.users backfill to migration
5. **Bug 15 incomplete**: Added eager `checkConfig()` on login + fallback timestamp on failure
6. **Bug 5 routing**: Noted TestPhotoService wrapping (agent will implement properly)
7. **Bug 16 RLS toast paths**: Added dedup guard to all 3 `onSyncErrorToast` call sites
8. **Wrong file paths**: Fixed 15 incorrect paths throughout plan
9. **Security H1 RPC allowlist**: Added table name allowlist to `get_table_integrity` RPC

### MEDIUM (4) — All Fixed
10. **Bug 10 query deviation**: Reverted to spec approach (just remove `.eq`, trust RLS)
11. **Bug 2 converter path**: Fixed to `lib/features/sync/adapters/type_converters.dart`
12. **Bug 2 22P02 reset**: Now targets `change_log` entries with 22P02 error_message
13. **Bug 9 supportsSoftDelete**: Confirmed already exists on `project_assignment_adapter.dart:27`

### LOW (accepted as-is)
- Phase 6 dispatch dependency is conservative but not harmful
- Bug 7 no validator test — covered by auth-agent during implementation
- Architecture doc update is minimal

## Security Conditions (all addressed)
- H1: RPC allowlist added with all 17 tables + project_assignments
- M1: Profile-completion redirect insertion point documented
- M2: `userId` field name corrected throughout
- L2: `kProfileMode` guard noted in plan for driver server

## Status: APPROVED (v2)
