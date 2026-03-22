# Retest Report — 2026-03-21 (S622 Retest of 8 FAIL flows)

## Summary
- **Platform**: Windows (desktop)
- **Retested**: 8 previously FAILED flows from S620
- **Result**: 7 PASS, 1 FAIL (T16 — missing inline edit field keys)
- **Fixes applied during retest**: 2 code changes + 1 Supabase role fix

## Results

| Flow | Previous | Retest | Notes |
|------|----------|--------|-------|
| T14 | FAIL | **PASS** | Filter toggle reveals search field; works correctly |
| T16 | FAIL | **FAIL** | `report_activities_field` key in constants but not on widget |
| T24 | FAIL | **PASS** | Location dropdown opens with keyed options after canEditEntry fix |
| T25 | FAIL | **PASS** | Weather dropdown opens with all 6 keyed options |
| T29 | FAIL | **PASS** | Undo button now visible; dialog needs confirm key (added) |
| T85 | FAIL | **PASS** | New Project FAB hidden for inspector (role was engineer, fixed) |
| T89 | FAIL | **PASS** | Archive toggle hidden for inspector |
| T90 | FAIL | **PASS** | Save button hidden in project edit (read-only for inspector) |

## Fixes Applied

1. **`auth_provider.dart:192-196`** — `canEditEntry` returns `true` for null `createdByUserId` (legacy pre-attribution entries editable by anyone with field-data permission)
2. **`entry_editor_screen.dart:305-312`** — Added `undo_cancel_button` and `undo_confirm_button` keys to undo submission dialog
3. **Supabase** — Inspector role restored from `engineer` → `inspector` via `update_member_role` RPC (was changed during T55 testing)

## Remaining FAIL

### T16: Inline Edit Field Keys (MEDIUM)
`report_activities_field`, `report_site_safety_field`, `report_sesc_field`, `report_traffic_field`, `report_visitors_field` — keys exist in `EntriesTestingKeys` but are not applied to the actual TextFormField/TextField widgets in the entry editor. These sections use tap-to-edit mode that renders text fields dynamically.

## Debug Server Logs
- 0 errors since retest start
