# Plan: New User Onboarding Flow Fix

**Created**: 2026-03-01
**Status**: READY FOR IMPLEMENTATION
**Blocker**: BLOCKER-15

## Problem

Router sends ALL `status=pending` users to "Pending Approval" regardless of `company_id`. First-time users with no company get trapped — no way to create a company or complete onboarding.

## Decisions Made (Brainstorming Session 470)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| First-user bootstrap | Hybrid — first user who creates a company = auto admin+approved; subsequent joiners need approval | Balances self-service with admin control |
| Status model | Check `companyId` nullability in router (no new DB status) | No migration needed, minimal change, existing screens already handle both flows |
| Restart with pending request | Auto-redirect to `/pending-approval` on CompanySetupScreen load | Best UX — user doesn't lose context after app restart |

## Security Analysis

**HARD CONSTRAINT: Security is non-negotiable.**

This fix is safe because the router is a UX navigation layer, NOT a security boundary:

- **Data access blocked regardless of screen**: `get_my_company_id()` returns NULL for non-approved users. All RLS policies use `company_id = get_my_company_id()` — NULL=NULL is false in SQL, so zero rows returned, zero writes allowed.
- **Locked fields cannot be changed client-side**: The `update_own_profile` RLS WITH CHECK forces `role`, `status`, `company_id` to match existing DB values. Only SECURITY DEFINER RPCs can change them.
- **Privilege transitions are server-side only**: `create_company()` RPC atomically sets admin+approved. `approve_join_request()` validates admin ownership.
- **Worst case (router removed entirely)**: User sees empty dashboard — no data exposure.

## Router Logic (After Fix)

```
if (profile != null) {
  // 2. No company yet -> company setup
  if (profile.companyId == null) {
    if (location == '/company-setup') return null;
    return '/company-setup';
  }

  // 3. Pending approval (has company, waiting for admin)
  if (status == MembershipStatus.pending) {
    if (location == '/pending-approval') return null;
    return '/pending-approval';
  }

  // 4. Rejected
  // 5. Deactivated
  // 6. Approved -- no redirect
}
```

### Routing Table

| User State | Router Destination |
|---|---|
| No profile | `/profile-setup` |
| Profile, no company | `/company-setup` |
| Profile + company + pending | `/pending-approval` |
| Profile + company + rejected | `/account-status?reason=rejected` |
| Profile + company + deactivated | `/account-status?reason=deactivated` |
| Profile + company + approved | Pass through (dashboard) |

## Edge Cases

| Scenario | Handling |
|---|---|
| First user creates company, kills app before router re-evaluates | `create_company()` RPC already committed server-side. On restart, `loadUserProfile()` fetches `status=approved` + `companyId` -> routes to dashboard. Safe. |
| User submits join request, kills app | Join request persists in DB. On restart, profile has `companyId=null` -> routes to `/company-setup`. Phase 2 auto-detects pending request and redirects to `/pending-approval`. |
| User has rejected join request, tries again | PendingApprovalScreen cancel -> `/company-setup`. User can search and join a different company. |
| Malicious client skips router, navigates to `/` | Dashboard renders but all queries return empty (RLS blocks). No data exposure. |
| Duplicate join request after restart | Unique index `idx_unique_pending_request` prevents duplicate pending requests to same company. |

## Key Files

| File | Change |
|------|--------|
| `lib/core/router/app_router.dart` | Reorder redirect checks: companyId null before pending status |
| `supabase/migrations/20260222100000_multi_tenant_foundation.sql` | Sync `handle_new_user()` with production (add `SET search_path = public` + schema-qualify) |
| `lib/features/auth/presentation/screens/company_setup_screen.dart` | Add pending join request check on load |

## Implementation Phases

### Phase 1: Router fix + migration sync (core fix)

**Files**: `app_router.dart`, `20260222100000_multi_tenant_foundation.sql`
**Agent**: `frontend-flutter-specialist-agent` (router), `backend-supabase-agent` (migration)

1. In `app_router.dart`, insert `companyId == null` check at line ~152, before the `status == pending` check
2. Allow `/company-setup` as the target route for users with no company
3. In migration file, update `handle_new_user()`:
   - Add `SET search_path = public` to function definition
   - Schema-qualify `public.user_profiles` in INSERT

**Gate**: Router correctly sends `companyId=null` users to `/company-setup` and `companyId!=null + pending` users to `/pending-approval`.

### Phase 2: Pending request check on CompanySetupScreen

**Files**: `company_setup_screen.dart`
**Agent**: `frontend-flutter-specialist-agent`

1. On `initState` (via `addPostFrameCallback`), query `JoinRequestRemoteDatasource.getByUser(userId)` for active pending requests
2. If a pending request exists, auto-navigate to `/pending-approval` with `requestId` and `companyName` from the request
3. Add loading state while checking (show CircularProgressIndicator)
4. Handle offline gracefully — if query fails, just show normal company setup screen (user can still create/join)

**Gate**: App restart during pending join request -> auto-redirects to `/pending-approval` with correct request details.

### Phase 3: E2E verification (manual device test)

**Agent**: Manual testing on Samsung S25 Ultra

Test cases:
1. Fresh signup -> profile setup -> company create -> dashboard (first user = admin+approved)
2. Second signup -> profile setup -> join company -> pending approval -> admin approves -> dashboard
3. Second signup -> profile setup -> join company -> pending approval -> cancel -> company-setup -> create own company
4. App kill during pending -> restart -> company-setup -> auto-redirect to pending-approval
5. Verify no data visible until approved (empty dashboard if router bypassed)
