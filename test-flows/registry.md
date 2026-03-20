# Unified Test Flow Registry

> Auto-updated by test agents after each run. Manual edits will be overwritten.

## Format
- **Driver Steps**: HTTP driver endpoint sequence (abbreviated)
- **Verify-Sync**: `verify-sync.ps1` invocation for data confirmation
- **Verify-Logs**: Debug server log categories to scan for errors
- **Status**: PASS / FAIL / UNTESTED / BLOCKED
- **Last Run**: ISO date of most recent execution

## Tier 1: Foundation (T01-T06)

> FIX CRIT-3: Flows now match spec exactly (project, location, contractor, equipment, pay item, assignment).

| ID | Flow | Table(s) | Driver Steps | Verify-Sync | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|-------------|--------|----------|-------|
| T01 | Create Project "E2E Test Project" | projects | tap(projects_nav) → tap(project_create) → text(project_name,"E2E Test Project") → text(project_number,"E2E-001") → tap(project_save) → wait(project_list) | -Table projects -Filter "name=like.E2E*" -CountOnly | sync,db | UNTESTED | - | |
| T02 | Add Location | locations | tap(project_card) → tap(project_locations_tab) → tap(project_add_location) → text(location_name,"E2E Location A") → tap(location_dialog_add) → tap(project_save) | -Table locations -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T03 | Add Contractor | contractors | tap(project_contractors_tab) → tap(project_add_contractor) → text(contractor_name,"E2E Contractor") → tap(contractor_save) | -Table contractors -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T04 | Add Equipment | equipment | tap(contractor_card) → tap(add_equipment) → text(equipment_name,"E2E Excavator") → tap(equipment_save) | -Table equipment -CountOnly | sync,db | UNTESTED | - | Depends: T03 |
| T05 | Add Pay Item | bid_items | tap(project_payitems_tab) → tap(add_bid_item) → text(bid_item_number,"E2E-100") → text(bid_item_desc,"E2E Test Item") → tap(bid_item_save) | -Table bid_items -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T06 | Add Project Assignment | project_assignments | tap(project_assignments_tab) → tap(add_assignment) → tap(user_select) → tap(assignment_save) | -Table project_assignments -CountOnly | sync,db | UNTESTED | - | Depends: T01 |

## Tier 2: Daily Entry Full Lifecycle (T07-T13)

| ID | Flow | Table(s) | Driver Steps | Verify-Sync | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|-------------|--------|----------|-------|
| T07 | Create Daily Entry | daily_entries | tap(calendar_nav) → tap(add_entry_fab) → wait(entry_wizard) → tap(entry_wizard_save_draft) | -Table daily_entries -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T08 | Add Personnel Log | entry_personnel_counts | tap(entry_card) → tap(personnel_tab) → tap(add_personnel) → text(personnel_count,"5") → tap(personnel_save) | -Table entry_personnel_counts -CountOnly | sync,db | UNTESTED | - | Depends: T07 |
| T09 | Add Equipment Usage | entry_equipment | tap(equipment_usage_tab) → tap(add_equipment_usage) → tap(select_equipment) → tap(equipment_usage_save) | -Table entry_equipment -CountOnly | sync,db | UNTESTED | - | Depends: T04,T07 |
| T10 | Log Quantities | entry_quantities | tap(quantities_tab) → tap(add_quantity) → tap(select_bid_item) → text(quantity_value,"10.5") → tap(quantity_save) | -Table entry_quantities -CountOnly | sync,db | UNTESTED | - | Depends: T05,T07 |
| T11 | Attach Photo (inject-photo) | photos | tap(photos_tab) → tap(add_photo) → inject-photo(test.jpg) → wait(photo_thumbnail) | -Table photos -CountOnly | sync,photo | UNTESTED | - | Depends: T07 |
| T12 | Create Todo | todo_items | tap(toolbox_nav) → tap(todos_tab) → tap(add_todo) → text(todo_title,"E2E Todo") → tap(todo_save) | -Table todo_items -CountOnly | sync,db | UNTESTED | - | Depends: T01 |
| T13 | Fill Inspector Form | inspector_forms | tap(toolbox_nav) → tap(forms_tab) → tap(add_form) → text(form_field,"E2E Form Data") → tap(form_save) | -Table inspector_forms -CountOnly | sync,db | UNTESTED | - | Depends: T01 |

## Tier 3: PDF Export (T14)

| ID | Flow | Table(s) | Driver Steps | Verify-Sync | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|-------------|--------|----------|-------|
| T14 | Export Daily Entry to PDF | N/A (local) | tap(entry_card) → tap(export_pdf) → wait(pdf_ready) → screenshot | N/A (verify file exists, non-zero bytes) | pdf | UNTESTED | - | Depends: T07 |

## Remaining Flows (from legacy registries — not yet migrated to HTTP driver)

> These flows existed in the old ADB and sync verification registries. They will be
> migrated to HTTP driver format in future phases. Listed here for tracking only.

### From legacy ADB flow registry (`.claude/test-flows/` old format)

**Smoke tier:**
- `login` — Auth smoke flow; verify login screen, enter credentials, confirm dashboard loads
- `navigate-tabs` — Navigation smoke; tap all 4 bottom nav tabs (Calendar, Projects, Settings, Dashboard)
- `create-entry-quick` — Entries smoke; tap add-entry FAB, save draft immediately, verify entry appears

**Feature tier — auth:**
- `register` — New user registration through OTP screen
- `forgot-password` — Forgot password via email, OTP verification screen check
- `profile-setup` — Complete inspector profile after registration (name, title)
- `company-setup` — Company selection or creation during onboarding

**Feature tier — projects:**
- `create-project` — Create project "ADB Test Project YYYY-MM-DD" with number and client fields
- `edit-project` — Open existing project, add a location via the Locations tab, save

**Feature tier — entries:**
- `create-entry` — Full entry with location, activities text, site safety, save draft
- `edit-entry` — Open today's entry, append " - edited via ADB" to activities field
- `review-submit` — Dashboard → review drafts → select all → mark ready → submit batch
- `create-entry-day2` — Navigate to a second date, create another draft entry
- `create-entry-offline` — Disable WiFi+data via ADB, create entry while offline, re-enable after

**Feature tier — contractors:**
- `add-contractors` — Add Prime and Sub contractors to a project via Contractors tab
- `add-contractors-entry` — Add a project contractor to an existing daily entry

**Feature tier — quantities:**
- `add-quantities` — Add pay item "101 - HMA Surface Course / 500 TON" manually via Pay Items tab
- `quantities-check` — Dashboard quantities card → verify bid items display correct totals

**Feature tier — photos:**
- `capture-photo` — Open entry, attach photo via camera or gallery, name and save

**Feature tier — sync:**
- `sync-check` — Settings → manual sync → verify status indicator and last sync timestamp
- `sync-reconnect` — Re-enable connectivity after offline test, trigger sync, verify entry pushes

**Feature tier — settings:**
- `settings-theme` — Switch theme Dark → Light, verify visual change
- `edit-profile` — Edit inspector name to "ADB Test Inspector" and initials to "ATI"
- `admin-dashboard` — Access admin panel in Settings (SKIP if user is not admin)
- `approve-member` — Approve pending member request from admin dashboard (SKIP if none exist)

**Feature tier — toolbox:**
- `calculator` — Open HMA calculator, enter area/thickness/density, verify result card
- `forms-fill` — Open first available form, fill visible fields, save
- `gallery-browse` — Open gallery, verify grid or empty state, check filter button
- `todos-crud` — Create todo "ADB Test Todo", verify in list, edit

**Journeys (J1-J12):**
- `J1: onboarding` — register → profile-setup → company-setup
- `J2: daily-work` — login → create-project → create-entry → add-quantities → review-submit → sync-check
- `J3: project-setup` — login → create-project → edit-project → import-pdf → add-contractors
- `J4: field-documentation` — login → create-entry → capture-photo → forms-fill → add-quantities
- `J5: offline-sync` — login → create-entry-offline → sync-reconnect
- `J6: admin-flow` — login → admin-dashboard → approve-member
- `J7: budget-tracking` — login → create-project → import-pdf → add-quantities → quantities-check
- `J8: entry-lifecycle` — login → create-entry → edit-entry → capture-photo → review-submit
- `J9: multi-day` — login → create-entry → create-entry-day2 → review-submit
- `J10: contractor-mgmt` — login → create-project → add-contractors → create-entry → add-contractors-entry
- `J11: settings-personalization` — login → settings-theme → edit-profile → todos-crud
- `J12: data-recovery` — login → create-entry-offline → sync-reconnect → edit-entry → sync-check

### From legacy sync verification registry (`.claude/test_results/flow_registry.md`)

**Tier 3: Mutations (old numbering T14-T20):**
- `old-T14` (Edit Project + Push) — projects table; edit and verify sync push
- `old-T15` (Edit Entry + Push) — daily_entries; edit existing entry and verify push
- `old-T16` (Delete Location + Push) — locations; delete location, verify removal syncs
- `old-T17` (Delete Contractor + Push) — contractors; delete contractor, verify removal syncs
- `old-T18` (Complete Todo + Push) — todo_items; mark todo complete, verify push
- `old-T19` (Archive Project + Push) — projects; archive project, verify status sync
- `old-T20` (Unarchive Project + Push) — projects; unarchive project, verify status sync

**Tier 4: Sync Engine Mechanics (old T21-T27):**
- `old-T21` (Pull After Remote Edit) — pull remote changes after external edit, verify local update
- `old-T22` (Offline Queue + Reconnect) — queue operations offline, reconnect, verify all flush
- `old-T23` (Conflict Resolution) — daily_entries; concurrent edit conflict, verify winner logic
- `old-T24` (Circuit Breaker Trip) — push_queue, sync_status; trigger circuit breaker, verify state
- `old-T25` (Circuit Breaker Resume) — verify circuit breaker resets and sync resumes; depends old-T24
- `old-T26` (Cursor Integrity Check) — verify pagination cursors are consistent across sync cycles
- `old-T27` (Orphan Photo Cleanup) — photos; verify orphaned photos are cleaned up; depends T11

**Tier 5: Role & Permission Verification (old T28-T31):**
- `old-T28` (Admin Full Access) — all tables; admin JWT full CRUD access
- `old-T29` (Engineer Edit Access) — varies; engineer role edit permissions
- `old-T30` (Inspector Read + Entry) — varies; inspector role can read and create entries
- `old-T31` (RLS Enforcement) — projects; MUST use real user JWT (not service role) to validate RLS

**Tier 6: Bug Regression (old T32-T39):**
- `old-T32` (BUG-006: Online recovery) — sync_status; depends old-T22
- `old-T33` (BUG-005: synced_projects enrollment) — synced_projects (SQLite-only)
- `old-T34` (BUG-007: Route guard /project/new) — projects
- `old-T35` (BUG-004: Assignment push after error) — project_assignments
- `old-T36` (BUG-001: Selected project clear) — projects
- `old-T37` (BUG-008: Inspector canWrite guard) — projects
- `old-T38` (BUG-009: Archive permission guard) — projects
- `old-T39` (BUG-010: Setup read-only mode) — projects

**Tier 7: Coverage Gaps (old T40-T42):**
- `old-T40` (Unassign Member + Push) — project_assignments; depends T06
- `old-T41` (User Profile Edit + Push) — user_profiles
- `old-T42` (Company Request + Push) — company_requests

## Auto-Update Protocol

After each test run, the agent MUST update:
1. **Status** column: PASS or FAIL
2. **Last Run** column: ISO date (e.g., 2026-03-19)
3. **Notes** column: failure reason if FAIL, cleared on PASS
