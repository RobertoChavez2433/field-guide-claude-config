# Tier 11: Role & Permission Verification (T85-T91)

> Switch to inspector role and verify restricted actions are blocked.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T85 | Inspector: No Create Project FAB | N/A | login_as(inspector) → tap(projects_nav) → screenshot → assert_not_visible(project_create_fab) | auth | Depends: T04; FAB must be absent |
| T86 | Inspector: No Admin Dashboard | N/A | tap(settings_nav) → screenshot → assert_not_visible(admin_dashboard_tile) | auth | Depends: T04 |
| T87 | Inspector: Can Create Entry | daily_entries | tap(calendar_nav) → tap(add_entry_fab) → tap(location_dropdown) → tap(location_select_a) → text(activities,"Inspector entry") → tap(save_draft) | sync,db,auth | Depends: T04,T06 |
| T88 | Inspector: Can Create Todo | todo_items | tap(toolbox_nav) → tap(todos_tile) → tap(add_todo_fab) → text(todo_title,"Inspector Todo") → tap(todo_save) | sync,db | Depends: T04 |
| T89 | Inspector: Cannot Archive Project | N/A | tap(projects_nav) → tap(project_card) → screenshot → assert_not_visible(archive_btn) | auth | Depends: T04 |
| T90 | Inspector: Project Edit Read-Only | N/A | tap(project_card) → tap(project_edit) → screenshot → assert_not_visible(project_save_btn) | auth | Depends: T04; fields should be read-only |
| T91 | Inspector: Route Guard /project/new | N/A | POST /driver/navigate {"path":"/project/new"} → wait(projects_screen) → screenshot | auth,nav | Depends: T04; should redirect to /projects; uses /driver/navigate endpoint |

---

# Tier 12: Navigation & Dashboard (T92-T96)

> Verify dashboard cards, quick stats links, and deep navigation paths.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T92 | Dashboard → Entries List | N/A | tap(dashboard_nav) → tap(entries_stat_card) → wait(entries_list_screen) → screenshot | nav | Depends: T15 |
| T93 | Dashboard → Quantities | N/A | tap(dashboard_nav) → tap(payitems_stat_card) → wait(quantities_screen) → screenshot | nav | Depends: T11 |
| T94 | Dashboard → Toolbox | N/A | tap(dashboard_nav) → tap(toolbox_stat_card) → wait(toolbox_screen) → screenshot | nav | Depends: T01 |
| T95 | Quantities → Bid Item Detail | N/A | tap(quantities_screen) → tap(bid_item_card) → wait(bid_item_detail_sheet) → screenshot | nav | BUG-17 fix verified — 2 pay items after re-login |
| T96 | Gallery → Photo Viewer | N/A | tap(toolbox_nav) → tap(gallery_tile) → tap(photo_thumbnail) → wait(photo_viewer) → screenshot | nav | BUG-17 fix verified — 2 photos in gallery after re-login |
