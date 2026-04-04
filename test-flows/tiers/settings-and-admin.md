# Tier 6: Settings & Profile (T44-T52)

> App settings and user profile management.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T44 | Edit Profile | user_profiles | tap(settings_nav) → tap(edit_profile_tile) → text(display_name,"E2E Test Admin") → text(cert_number,"CERT-001") → text(phone,"5551234567") → text(initials,"ETA") → tap(save_profile) | sync,db | Profile name field + save button accessible |
| T45 | Change Theme | N/A | tap(settings_nav) → tap(theme_toggle) → screenshot → tap(theme_toggle) → screenshot | ui | Depends: T01; visual verification via screenshot |
| T46 | Edit Gauge Number | N/A (local pref) | tap(settings_nav) → tap(gauge_number_tile) → text(gauge_number_field,"12345") → tap(gauge_save) → screenshot | db | Dialog keys accessible on fresh launch |
| T47 | Edit Initials | N/A (local pref) | tap(settings_nav) → tap(initials_tile) → text(initials_field,"TST") → tap(initials_save) → screenshot | db | Dialog keys accessible on fresh launch |
| T48 | Toggle Auto-Load Last Project | N/A (local pref) | tap(settings_nav) → tap(auto_load_toggle) → screenshot | ui | Depends: T01 |
| T49 | View Sync Dashboard | N/A | tap(settings_nav) → tap(sync_dashboard_tile) → wait(sync_dashboard_screen) → screenshot | sync | Depends: T01 |
| T51 | Restore from Trash | varies | tap(settings_nav) → tap(trash_tile) → wait(trash_screen) → tap(restore_btn) → tap(restore_confirm) → screenshot | db | Depends: T30 (needs a deleted entry) |
| T52 | Clear Cached Exports | N/A | tap(settings_nav) → tap(clear_cache_tile) → tap(clear_cache_confirm) → screenshot | db | Depends: T01 |

---

# Tier 7: Admin Operations (T53-T58)

> Admin-only flows. Requires admin login (T01).

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T53 | Open Admin Dashboard | N/A | tap(settings_nav) → tap(admin_dashboard_tile) → wait(admin_dashboard_screen) → screenshot | nav | Depends: T01 (admin) |
| T54 | View Team Members | user_profiles | tap(team_member_card) → wait(member_detail_sheet) → screenshot | db | Depends: T53 |
| T55 | Change Member Role | user_profiles | tap(team_member_card) → tap(role_dropdown) → tap(role_engineer) → tap(role_save_confirm) → screenshot | sync,db | Depends: T53; changes inspector→engineer |
| T56 | Approve Join Request | company_join_requests | tap(pending_request_card) → tap(approve_role_inspector) → tap(approve_confirm) → screenshot | sync,auth | Requires a pending join request + second account |
| T57 | Reject Join Request | company_join_requests | tap(pending_request_card) → tap(reject_btn) → tap(reject_confirm) → screenshot | sync,auth | Requires a pending join request + second account |
| T58 | Archive Project | projects | tap(projects_nav) → tap(archive_btn) → wait(project_archived) → tap(archived_tab) → screenshot | sync,db | Depends: T05 |
