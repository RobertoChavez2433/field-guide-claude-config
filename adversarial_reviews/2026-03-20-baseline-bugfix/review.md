# Adversarial Review: Baseline Bug Fix Spec

**Spec**: `.claude/specs/2026-03-20-baseline-bugfix-spec.md`
**Date**: 2026-03-20
**Reviewers**: code-review-agent, security-agent

## MUST-FIX (5 items — all addressed in spec v2)

### 1. Bug 1: User filter + fresh-restore guard
- **Code Review**: Fresh-restore scenario not covered — cursor set but local tables empty
- **Security**: Enrollment must filter `project_assignments` by `user_id = currentUserId`
- **Resolution**: Added both to spec — user filter on enrollment, cursor reset if both tables empty

### 2. Bug 2: Error reset too broad
- **Both reviewers**: Resetting ALL error-state todos masks legitimate errors
- **Resolution**: Scoped to `last_sync_error LIKE '%22P02%'`, added logging

### 3. Bug 6: FormField assertion crash
- **Code Review**: Can't have both `initialValue` and `value` — runtime assertion
- **Resolution**: Spec updated to "remove and replace" not "rename"

### 4. Bug 7: Server-side length constraint
- **Security**: `raw_user_meta_data` is user-controllable via direct API calls
- **Resolution**: Added `SUBSTR(TRIM(...), 1, 200)` in trigger and backfill

### 5. Bug 9: Deployment order
- **Code Review**: RPC must be updated before Dart client to avoid false drift
- **Resolution**: Spec prescribes RPC migration first

## SHOULD-CONSIDER (7 items — for implementation plan)

1. **Bug 2**: Fix `toMap()` to output `priority.index` instead of converter band-aid
2. **Bug 3**: Document `architecture.md` deviation (addPostFrameCallback → didChangeDependencies)
3. **Bug 5**: Add `kProfileMode` guard, strip EXIF on direct-inject, inherit validation
4. **Bug 7**: Profile-completion gate for existing NULL-name users
5. **Bug 10**: Assert orphan path starts with `entries/{companyId}/` before deletion
6. **Bug 16**: SyncProvider dedup flag instead of `clearSnackBars()` (avoids clearing non-sync snackbars)
7. **Bug 11**: Enum for section parameter instead of free string

## Security Implications

- Bug 1: RLS enforces company-level scoping but NOT assignment-level. Inspector on rooted device could manipulate local SQLite to pull unassigned project data within their company. Pre-existing architectural gap — not introduced by this fix, but enrollment user-filter is critical.
- Bug 5: Profile builds expose driver server. Direct-inject bypasses EXIF stripping. GPS metadata could leak to Supabase if test photo is synced.
- Bug 7: `raw_user_meta_data` is user-writable. Display name appears in legally significant PDFs. Content injection risk for report formatting. Server-side length constraint is minimum defense.
- Bug 10: RLS on photos table correctly scopes to company via project_id. Storage bucket policies scope via folder path prefix. Removing invalid `.eq('company_id')` does not weaken security.

## Codebase Pattern Compliance

- Bug 2 error reset should be a versioned migration (DatabaseService.onUpgrade), not ad-hoc startup logic
- Bug 3 didChangeDependencies deviates from architecture.md recommendation of addPostFrameCallback — justified but should be documented
- Bug 5 PhotoRepository injection into DriverServer couples test infrastructure to production data layer — consider wrapping via TestPhotoService method instead
