# Plan Completeness Audit

**Date**: 2026-02-22
**Branch**: feature/phase-4-firebase-background-sync
**Auditor**: code-review-agent (exhaustive line-by-line)
**Items Checked**: 312 | **PASS**: 247 | **FAIL**: 42 | **SKIP**: 23

## Fix Status Legend
- FIXED = Already resolved by fix agents this session
- OPEN = Still needs fixing
- EXTERNAL = Requires manual/external action (not code)

## Critical Gaps (15 items)

| # | Phase | Description | Status |
|---|-------|-------------|--------|
| 1 | 1B | UserRole enum: `member` vs Supabase `engineer/inspector` | FIXED |
| 2 | 2A | `loadUserProfile()` never called after sign-in/sign-up | OPEN |
| 3 | 1C | `user_profiles` local schema: `company_id NOT NULL` should be nullable | OPEN |
| 4 | 1C | `user_profiles` local schema: `display_name NOT NULL` should be nullable | OPEN |
| 5 | 2A | `search_companies` RPC param `search_query` vs `query` | OPEN |
| 6 | 3D | Photo storage uses `getPublicUrl()` not `createSignedUrl()` (SEC-2) | OPEN |
| 7 | 3D | No client-side company scoping on pull queries (HIGH-11) | OPEN |
| 8 | 3C | CONT-16: Forms/Calculator/Todo use legacy SyncService | FIXED |
| 9 | 4B/C | No Firebase platform config (google-services, Info.plist) | EXTERNAL |
| 10 | 4E | FCM tokens migration SQL missing | OPEN |
| 11 | D17 | WAL mode not enabled for SQLite | OPEN |
| 12 | 1C | entry_personnel_counts missing created_at/updated_at in fresh schema | OPEN |
| 13 | 3C | entry_personnel not removed from sync (CONT-8) | OPEN |
| 14 | 3D | Photo upload path not restructured to company-scoped | OPEN |
| 15 | D16 | deleteAll() unrestricted in production | OPEN |

## Non-Critical Gaps (20 items)

| # | Phase | Description | Priority |
|---|-------|-------------|----------|
| 1 | 3E | user_profile_sync_datasource.dart missing | Medium |
| 2 | 3E | clearLocalCompanyData() not implemented | Medium |
| 3 | 3E | SharedPreferences not cleared on sign-out | Medium |
| 4 | 0 | Release-mode Supabase guard missing | Low |
| 5 | 8 | Mock auth release-mode assertion missing | Low |
| 6 | 7B | Photo thumbnail attribution missing | Low |
| 7 | 2D | CONT-18: Route restoration exclusion not implemented | Low |
| 8 | 2D | /admin-dashboard router guard missing | Medium |
| 9 | 3C | Stale-data MaterialBanner not implemented | Medium |
| 10 | 5A | project_switcher_sheet.dart not separate file | Low |
| 11 | 7A | UserAttributionRepository not in repositories barrel | Low |
| 12 | 8B | Todos screen FAB visible to viewers | Medium |
| 13 | 8B | Forms list create buttons visible to viewers | Medium |
| 14 | 2A | HIGH-9: Mock auth returns no UserProfile | Medium |
| 15 | 4E | Edge Function not created | Low |
| 16 | 3D | SEC-NEW-7: _validateStoragePath() not implemented | Low |
| 17 | 7C | pdf_service.dart not directly modified | Low |
| 18 | 2C | InspectorProfileSection widget file still exists | Low |
| 19 | 3D | entry_contractors/entry_personnel_counts missing updated_at | Medium |
| 20 | 2D | Cancel join request uses UPDATE not DELETE | Low |
