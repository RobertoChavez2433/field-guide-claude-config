# E2E Sync Verification System Spec

**Date**: 2026-03-19
**Status**: Approved (post-review)
**Branch**: feat/sync-engine-rewrite
**Review**: `.claude/adversarial_reviews/2026-03-19-e2e-sync-verification/review.md`

## Overview

### Purpose
Build a reusable e2e sync verification system that lets Claude (or a human) test all 17 synced tables end-to-end: create/edit/delete data in the app → verify it lands correctly in Supabase → verify pull back to the app.

### Scope

**Included:**
- Add ~30 missing testing keys to sync/project UI widgets
- Align `flutter_driver` (for driving/coordinates) with the HTTP debug server (for diagnostics/logs) as a unified testing toolkit
- Add `/sync/status` endpoint to the debug server for sync-completion polling
- Supabase REST API verification commands (PowerShell-based, queryable per table/project)
- Comprehensive e2e test flow checklist covering all 17 tables, sync lifecycle, conflict resolution, offline queue, role permissions, and 14 known bugs (42 flows total)
- Structured test output format with date-stamped runs, per-flow results, and persistent flow registry

**Excluded:**
- PDF extraction during project creation (manual quantity entry instead)
- Two-instance Windows testing (deferred until code change for separate data dirs)
- Fixing the 14 known bugs (this spec is the verification system, not the fix)

### Success Criteria
- Every interactive sync/project element has a testing key
- `flutter_driver` can locate any testing key and return its screen coordinates
- HTTP debug server provides real-time sync status, log diagnostics, and key positions
- Each of the 17 synced tables has a documented verification flow with exact Supabase query
- Test flows are ordered so they can be run sequentially in a single session
- All test results documented in structured format with screenshots and Supabase verification output
- All test data uses `E2E ` prefix for safe identification and cleanup

---

## Testing Keys Addition

### New File: `lib/shared/testing_keys/sync_keys.dart`

| Key | Widget | Screen |
|-----|--------|--------|
| `syncNowTile` | "Sync Now" ListTile | SyncDashboard |
| `syncViewConflictsTile` | "View Conflicts" ListTile | SyncDashboard |
| `syncViewProjectsTile` | "View Synced Projects" ListTile | SyncDashboard |
| `syncResumeSyncButton` | Circuit breaker "RESUME SYNC" | SyncDashboard |
| `syncBucketTile(name)` | Pending bucket ExpansionTile | SyncDashboard |
| `syncStatusBadge` | Status badge (idle/syncing/error) | SyncDashboard |
| `syncLastSyncTimestamp` | Last sync time text | SyncDashboard |

### Additions to `lib/shared/testing_keys/projects_keys.dart`

| Key | Widget | Screen |
|-----|--------|--------|
| `projectTabMyProjects` | "My Projects" tab | ProjectList |
| `projectTabCompany` | "Company" tab | ProjectList |
| `projectTabArchived` | "Archived" tab | ProjectList |
| `projectFilterAll` | "All" chip | ProjectFilterChips |
| `projectFilterOnDevice` | "On Device" chip | ProjectFilterChips |
| `projectFilterNotDownloaded` | "Not Downloaded" chip | ProjectFilterChips |
| `projectDownloadButton(id)` | Download button on remote card | ProjectList |
| `projectDownloadDialogCancel` | Download dialog Cancel | ProjectList |
| `projectDownloadDialogConfirm` | Download dialog Download | ProjectList |
| `projectRemoteDeleteDialogCancel` | Remote delete Cancel | ProjectList |
| `projectRemoteDeleteDialogConfirm` | Remote delete Confirm | ProjectList |
| `projectBrowseButton` | "Browse Available" empty state | ProjectEmptyState |
| `projectDescriptionField` | Description TextFormField | ProjectDetailsForm |
| `projectDiscardButton` | Back nav "Discard" | ProjectSetup |
| `projectSaveDraftButton` | Back nav "Save Draft" | ProjectSetup |
| `removalDialogCancel` | Cancel | RemovalDialog |
| `removalDialogSyncAndRemove` | "Sync & Remove" | RemovalDialog |
| `removalDialogDeleteFromDevice` | "Delete from Device" | RemovalDialog |
| `assignmentSearchField` | Member search | AssignmentsStep |
| `assignmentTile(userId)` | Assignment row | AssignmentsStep |
| `projectSwitcher` | Switcher trigger | ProjectSwitcher |
| `projectSwitcherViewAll` | "View All" item | ProjectSwitcher |
| `projectSwitcherNewProject` | "+ New Project" item | ProjectSwitcher |
| `projectSwitcherTile(id)` | Recent project item | ProjectSwitcher |

### Widget Files to Update (apply keys to widgets)

- `sync_dashboard_screen.dart` — sync keys
- `project_list_screen.dart` — tab, dialog, download keys
- `project_filter_chips.dart` — filter chip keys
- `project_tab_bar.dart` — tab keys
- `removal_dialog.dart` — dialog keys
- `assignments_step.dart` — assignment keys
- `project_empty_state.dart` — browse button key

---

## App Driving & Diagnostics Architecture

### Design: flutter_driver + HTTP Debug Server

Two complementary systems working together:

**flutter_driver** (existing in pubspec) — for driving the app:
- `FlutterDriver.getCenter(find.byValueKey('key_name'))` — get coordinates for any testing key
- Handles off-screen widgets automatically (scrolls into view)
- Handles dialog-only widgets (waits for presence)
- Tap, enter text, scroll, take screenshots
- Connects via VM service port (no custom HTTP port needed)

**HTTP Debug Server** (existing at port 3947) — for diagnostics:
- Real-time sync logs via `GET /logs?category=sync`
- Hypothesis testing via `Logger.hypothesis()`
- Error categorization visibility
- **New endpoint**: `POST /sync/status` — app pushes sync state changes (started, completed, failed, table progress)
- **New endpoint**: `GET /sync/status` — Claude polls for current sync state

### Sync Status Integration

The app already POSTs logs to port 3947. Extend this with structured sync lifecycle events:

```json
// App POSTs to debug server on sync state changes:
{"type": "sync_status", "state": "started", "timestamp": "..."}
{"type": "sync_status", "state": "push_table", "table": "daily_entries", "count": 5}
{"type": "sync_status", "state": "pull_table", "table": "locations", "cursor": "2026-03-19T..."}
{"type": "sync_status", "state": "completed", "pushed": 12, "pulled": 8, "errors": 0}
{"type": "sync_status", "state": "failed", "error": "SocketException", "table": "projects"}
```

The debug server stores the latest sync status and exposes it via `GET /sync/status`:
```json
{"state": "completed", "pushed": 12, "pulled": 8, "errors": 0, "timestamp": "..."}
```

### Guards

- `flutter_driver` extension: enabled via `enableFlutterDriverExtension()` in test harness entry point, or via `--enable-vmservice-publication` flag
- Debug server POST: existing `kReleaseMode` + `DEBUG_SERVER` guard in `logger.dart`
- **Origin header check**: Debug server already blocks browser requests (`server.js:230`). Sync status endpoint inherits this protection.

---

## Supabase Verification Layer

### Approach

Supabase REST API (PostgREST) via PowerShell `Invoke-RestMethod`.

### Credential Storage

**CRITICAL**: Service role key must NOT be stored in `.env` (which contains the anon key for app builds).

Store in `.env.secret`:
```
SUPABASE_SERVICE_ROLE_KEY=<key>
```

`.env.secret` must be in `.gitignore`. The verification script reads from this separate file.

### Script: `tools/verify-sync.ps1`

Parameters:
- `-Table <name>` — which table to query
- `-ProjectId <id>` — scope to project (optional)
- `-Filter <string>` — PostgREST filter (e.g., `name=eq.E2E Test`)
- `-CountOnly` — return row count only
- `-Cleanup -ProjectName <name>` — delete test data (MUST start with "E2E ")
- `-WhatIf` — dry-run mode for cleanup (show what would be deleted)

Reads `SUPABASE_URL` from `.env`, `SUPABASE_SERVICE_ROLE_KEY` from `.env.secret`. Authorization headers are NEVER written to output files.

### Cleanup Safety

The `-Cleanup` flag enforces:
1. `-ProjectName` must start with `"E2E "` — rejects otherwise
2. `-WhatIf` dry-run available to preview deletions
3. No wildcard support
4. Cascading delete: project → all child tables (locations, contractors, entries, etc.)

### Verification Queries per Table (CORRECTED TABLE NAMES)

| Table | Query Scope | Key Fields |
|-------|------------|------------|
| `projects` | `?id=eq.<id>` | name, number, client, is_active, deleted_at |
| `project_assignments` | `?project_id=eq.<id>` | user_id, assigned_by, company_id |
| `locations` | `?project_id=eq.<id>` | name, description, sort_order |
| `contractors` | `?project_id=eq.<id>` | name, type |
| `equipment` | `?contractor_id=eq.<id>` | name, description |
| `bid_items` | `?project_id=eq.<id>` | item_number, description, quantity, unit |
| `daily_entries` | `?project_id=eq.<id>` | location_id, date, weather_data |
| `entry_personnel_counts` | `?entry_id=eq.<id>` | contractor_id, count, hours |
| `entry_equipment` | `?entry_id=eq.<id>` | equipment_id, hours, idle_hours |
| `entry_quantities` | `?entry_id=eq.<id>` | bid_item_id, quantity, station |
| `photos` | `?project_id=eq.<id>` | entry_id, storage_path, caption |
| `inspector_forms` | `?project_id=eq.<id>` | template_id, data, status |
| `todo_items` | `?project_id=eq.<id>` | title, is_completed, assigned_to |
| `user_profiles` | `?id=eq.<uid>` | display_name, email, role |
| `company_requests` | `?user_id=eq.<uid>` | company_id, status |
| `synced_projects` | *(local SQLite only)* | project_id, last_pulled_at |

**Note**: `synced_projects` is local-only. Verification for T33 uses SQLite query via flutter_driver, not PostgREST.

---

## E2E Test Flow Checklist

### Test Data Convention

All test data MUST use `E2E ` prefix:
- Project name: `"E2E Test Project Alpha"`
- Location names: `"E2E Main Building"`, `"E2E Parking Lot"`
- Contractor names: `"E2E Prime Contractor"`, `"E2E Sub Contractor"`
- Todo titles: `"E2E Inspect foundation"`

This enables safe cleanup and prevents confusion with production data.

### Tier 1: Foundation (must pass before anything else)

| Flow | Name | Steps | Supabase Verification |
|------|------|-------|----------------------|
| T01 | Project Create + Push | Create project "E2E Test Project Alpha" with number/client → Save → Sync | `projects` row exists with matching fields, `company_id` set |
| T02 | Location Add + Push | Add 2 locations to T01 project → Save → Sync | `locations` has 2 rows for project_id |
| T03 | Contractor Add + Push | Add 1 prime + 1 sub contractor → Save → Sync | `contractors` has 2 rows, correct types |
| T04 | Equipment Add + Push | Add equipment to T03 contractor → Save → Sync | `equipment` row linked to contractor_id |
| T05 | Pay Item Add + Push | Manually add 3 pay items (no PDF) → Save → Sync | `bid_items` has 3 rows with number/desc/qty/unit |
| T06 | Project Assignment + Push | Assign a team member on Assignments tab → Sync | `project_assignments` row with correct user_id, assigned_by |

### Tier 2: Daily Workflow (entry creation and child records)

| Flow | Name | Steps | Supabase Verification |
|------|------|-------|----------------------|
| T07 | Entry Create + Push | New daily entry on T01 project, select location → Save → Sync | `daily_entries` row with project_id, location_id, date |
| T08 | Personnel Log + Push | Add personnel to T07 entry (contractor, count, hours) → Save → Sync | `entry_personnel_counts` row linked to entry_id |
| T09 | Equipment Usage + Push | Log equipment hours on T07 entry → Save → Sync | `entry_equipment` row with hours |
| T10 | Quantity Log + Push | Record quantity against a pay item → Save → Sync | `entry_quantities` row with bid_item_id, quantity |
| T11 | Photo Attach + Push | Capture/attach photo to entry → Sync | `photos` row with storage_path populated, file exists in Supabase Storage |
| T12 | Todo Create + Push | Create todo "E2E Inspect foundation" → Sync | `todo_items` row with title, is_completed=false |
| T13 | Form Create + Push | Create a form entry → Sync | `inspector_forms` row with template_id, data JSON |

### Tier 3: Mutations (edit, delete, soft-delete)

| Flow | Name | Steps | Supabase Verification |
|------|------|-------|----------------------|
| T14 | Edit Project + Push | Change project name → Save → Sync | `projects.name` updated, `updated_at` advanced |
| T15 | Edit Entry + Push | Modify entry notes/weather → Save → Sync | `daily_entries` row reflects edits |
| T16 | Delete Location + Push | Remove a location → Sync | `locations` row has `deleted_at` set (soft-delete) |
| T17 | Delete Contractor + Push | Remove a contractor → Sync | `contractors` row has `deleted_at` set |
| T18 | Complete Todo + Push | Mark todo complete → Sync | `todo_items.is_completed=true` |
| T19 | Archive Project + Push | Archive T01 project → Sync | `projects.is_active=false` |
| T20 | Unarchive Project + Push | Restore archived project → Sync | `projects.is_active=true` |

### Tier 4: Sync Engine Mechanics

| Flow | Name | Steps | Verification |
|------|------|-------|-------------|
| T21 | Pull After Remote Edit | Edit a row directly in Supabase → Trigger sync in app | App shows updated value (screenshot verify) |
| T22 | Offline Queue + Reconnect | Go offline → Create entry → Reconnect → Auto-sync | Row appears in Supabase after reconnect |
| T23 | Conflict Resolution | Edit same row in app AND Supabase → Sync | Last-write-wins applied, `sync_status` records conflict |
| T24 | Circuit Breaker Trip | Flood change_log past threshold → Verify banner appears | Screenshot verify banner, `GET /sync/status` shows `circuit_breaker_tripped` |
| T25 | Circuit Breaker Resume | Dismiss banner → Verify sync resumes | `GET /sync/status` returns `completed`, pending changes pushed |
| T26 | Cursor Integrity Check | Delete rows directly in Supabase → Sync | Cursor resets, app re-pulls missing data |
| T27 | Orphan Photo Cleanup | Delete photo record in Supabase → Run orphan scan | Storage file removed after scan |

### Tier 5: Role & Permission Verification

| Flow | Name | Steps | Verification |
|------|------|-------|-------------|
| T28 | Admin Full Access | Verify admin can create/edit/delete/archive/assign | All operations succeed |
| T29 | Engineer Edit Access | Verify engineer can create entries, edit, but not delete projects | Operations gated correctly |
| T30 | Inspector Read + Entry | Verify inspector can create entries but not edit project setup | Edit buttons hidden/disabled (screenshot verify) |
| T31 | RLS Enforcement | Query Supabase REST API using authenticated JWT from test account, request data from a different company | Returns empty set (RLS blocks). **Must use user JWT, NOT service role key** |

### Tier 6: Bug Regression (run after fixes)

| Flow | Bug ID | Name | Verification |
|------|--------|------|-------------|
| T32 | BUG-006 | Online recovery after error | SocketException → DNS check → sync resumes. `GET /sync/status` returns `completed` |
| T33 | BUG-005 | synced_projects enrollment | After download, local `synced_projects` count matches enrolled projects (SQLite query via flutter_driver) |
| T34 | BUG-007 | Route guard /project/new | Inspector navigating to edit route gets redirected |
| T35 | BUG-004 | Assignment push after error | Assignment changes push after retry |
| T36 | BUG-001 | Selected project clear | removeFromDevice clears dashboard selection |
| T37 | BUG-008 | Inspector canWrite guard | Inspector sees no edit/archive buttons |
| T38 | BUG-009 | Archive permission guard | Inspector archive toggle blocked |
| T39 | BUG-010 | Setup read-only mode | Inspector sees read-only project setup |

### Tier 7: Coverage Gaps (added from review)

| Flow | Name | Steps | Verification |
|------|------|-------|-------------|
| T40 | Unassign Member + Push | Remove assignment from Assignments tab → Sync | `project_assignments` row has `unassigned_at` set |
| T41 | User Profile Edit + Push | Change display name in Settings → Sync | `user_profiles.display_name` updated in Supabase |
| T42 | Company Request + Push | Submit company join request → Sync | `company_requests` row with status='pending' |

### Flow Dependencies

```
T01 → T02, T03, T05, T06, T07, T14, T19
T03 → T04, T17
T04 → T09
T05 → T10
T06 → T40
T07 → T08, T09, T10, T11, T15
T11 → T27
T12 → T18
T19 → T20
T22 → T32
```

---

## Edge Cases & Error Handling

| Scenario | Expected Behavior | How to Test |
|----------|------------------|-------------|
| Sync during active edit | Unsaved form data preserved | Edit entry → trigger sync → verify fields unchanged |
| Network drop mid-push | Partial push retried on next cycle | Kill network mid-sync → reconnect → verify rows |
| Duplicate key (23505) | Retryable, resolved with upsert pre-check | Create project with existing natural key → sync |
| FK violation (23503) | Per-record blocking, children skipped | Push child before parent → verify parent-first retry |
| RLS deny (42501) | Permanent failure, logged, not retried | Push from wrong company → verify error log |
| Token expiry (401) | Token refresh, sync retries | Let session expire → sync → verify auto-refresh |
| Large batch push | 500+ entries process without timeout | Bulk-create offline → reconnect → verify 2 cycles |
| Concurrent sync trigger | Mutex prevents overlap | Rapid "Sync Now" taps → verify mutex log |
| App kill during sync | Heartbeat timeout recovers lock | Kill mid-sync → relaunch → verify recovery |
| Empty project pull | No errors on 0-child project | Enroll in empty project → verify clean sync |

---

## Test Output Format

### Directory Structure

```
test_results/
├── runs/
│   └── YYYY-MM-DD_run-NN/
│       ├── summary.md
│       ├── T01_project_create.md
│       ├── ...
│       └── screenshots/
└── latest.md

.claude/test_results/
└── flow_registry.md          # Persistent — lives OUTSIDE test_results/ gitignore
```

**IMPORTANT**: `flow_registry.md` lives in `.claude/test_results/` (tracked in claude config repo), NOT in `test_results/` (gitignored from app repo). This ensures persistence across sessions and machines.

### Per-Flow Result Template

```markdown
# TNN: Flow Name

**Date**: YYYY-MM-DD HH:MM
**Run**: YYYY-MM-DD_run-NN
**Status**: PASS | FAIL | BLOCKED | SKIPPED
**Blocked By**: (flow ID if BLOCKED)

## Preconditions
- (login state, prerequisite data)

## Steps Executed
1. (action with key name and coordinates)

## Expected Result
- (what should happen)

## Actual Result
- (what did happen, field-by-field comparison)

## Supabase Verification
(PowerShell command + result — authorization headers NEVER included)

## Debug Server Logs
(relevant sync log entries from GET /logs?category=sync&last=20)

## Screenshots
- [Before](screenshots/TNN_before.png)
- [After](screenshots/TNN_after.png)

## Notes
(observations, warnings)
```

### Run Summary Template

Header: date, device, account, app version (branch + commit), duration.
Tables: status counts, per-tier breakdown, failure details, blocked flows, action items.

### Flow Registry (`.claude/test_results/flow_registry.md`)

Persistent tracker: flow ID, name, latest status, last run date, last pass date, notes.
Updated after every run.

---

## Execution Model

### Day 0 Prerequisites

1. Add `test_results/` to `.gitignore` BEFORE creating any files
2. Create `.env.secret` with `SUPABASE_SERVICE_ROLE_KEY` (separate from `.env`)
3. Verify `.env.secret` is in `.gitignore`

### Pre-Run Setup

1. Launch debug server: `node tools/debug-server/server.js`
2. Launch app with debug + driver flags:
   ```
   pwsh -Command "flutter run -d windows --dart-define=DEBUG_SERVER=true --dart-define-from-file=.env"
   ```
3. Connect flutter_driver to the running app's VM service
4. Verify debug server health: `GET http://127.0.0.1:3947/health`
5. Verify Supabase connectivity: `.\tools\verify-sync.ps1 -Table projects -CountOnly`

### Per-Flow Execution

1. Use `flutter_driver` to find keys and get coordinates
2. Execute steps via flutter_driver (tap, enterText, scroll)
3. Take screenshot via flutter_driver after significant state changes
4. Trigger sync (tap `syncNowTile` key via driver)
5. Poll `GET /sync/status` on debug server until state=completed or timeout
6. Query debug server logs: `GET /logs?category=sync&last=50` for diagnostics
7. Run Supabase verification via `verify-sync.ps1`
8. Write result file to `test_results/runs/<date>_run-<N>/`

### Post-Run

1. Generate summary.md from individual results
2. Update `.claude/test_results/flow_registry.md` with latest statuses
3. Stop app + debug server

### Cleanup Options

- **Soft reset**: Archive test project (T19), create fresh for next run
- **Hard reset**: `verify-sync.ps1 -Cleanup -ProjectName "E2E Test Project Alpha"` (enforces E2E prefix)
- **Dry run**: `verify-sync.ps1 -Cleanup -ProjectName "E2E Test Project Alpha" -WhatIf`

### Device Adaptability

When mobile device available:
- Replace `flutter run -d windows` with `-d <serial>`
- ADB forwarding: `adb reverse tcp:3947 tcp:3947`
- Same flutter_driver connection, same verification queries, same output format
- Add `device` field to summary header

---

## Security

### flutter_driver Extension

- Only enabled in debug/profile builds (VM service not published in release)
- No custom port — uses Flutter's VM service protocol
- Existing pattern: `enableFlutterDriverExtension()` already in `lib/test_harness.dart`

### Debug Server (port 3947)

- Existing `Origin` header check blocks browser SSRF (`server.js:230`)
- New `/sync/status` endpoint inherits same protection
- Binds to `127.0.0.1` only

### Verification Script (`verify-sync.ps1`)

- Service role key from `.env.secret` (separate from `.env`, gitignored)
- Authorization headers NEVER written to output files
- `-Cleanup` enforces `E2E ` prefix on project names — rejects non-prefixed names
- `-WhatIf` dry-run available for cleanup preview
- No wildcard support in cleanup

### Test Data Isolation

- All test data uses `E2E ` naming prefix
- Uses existing account (no separate test company)
- Cleanup available via `-Cleanup` flag with prefix enforcement
- Test results in `test_results/` (gitignored from app repo)

### T31 RLS Test

T31 uses an authenticated user JWT (not service role key) to verify RLS enforcement. The service role key bypasses RLS and would give a false positive.

### No New RLS Policies

This spec does not affect Supabase RLS policies.

---

## New / Modified Files

### New Files

| File | Purpose |
|------|---------|
| `lib/shared/testing_keys/sync_keys.dart` | Sync dashboard keys (~7 keys) |
| `tools/verify-sync.ps1` | Supabase REST verification helper |
| `.claude/test_results/flow_registry.md` | Persistent flow status tracker |
| `.env.secret` | Service role key (gitignored) |

### Modified Files

| File | Change |
|------|--------|
| `lib/shared/testing_keys/projects_keys.dart` | Add ~24 missing keys |
| `lib/shared/testing_keys/testing_keys.dart` | Re-export sync_keys, add new project keys to facade |
| `tools/debug-server/server.js` | Add `POST /sync/status` and `GET /sync/status` endpoints |
| `lib/features/sync/engine/sync_engine.dart` | POST sync lifecycle events to debug server |
| `lib/features/sync/presentation/screens/sync_dashboard_screen.dart` | Apply sync testing keys |
| `lib/features/projects/presentation/screens/project_list_screen.dart` | Apply tab/dialog/download keys |
| `lib/features/projects/presentation/widgets/project_filter_chips.dart` | Apply filter chip keys |
| `lib/features/projects/presentation/widgets/project_tab_bar.dart` | Apply tab keys |
| `lib/features/projects/presentation/widgets/removal_dialog.dart` | Apply dialog keys |
| `lib/features/projects/presentation/widgets/assignments_step.dart` | Apply assignment keys |
| `lib/features/projects/presentation/widgets/project_empty_state.dart` | Apply browse button key |
| `.gitignore` | Add `test_results/` and `.env.secret` |

### No Schema Changes

No SQLite or Supabase migrations required.

---

## Decisions Log

| Decision | Choice | Rationale | Alternatives Rejected |
|----------|--------|-----------|----------------------|
| App driving method | flutter_driver + HTTP debug server | Leverage existing infrastructure; driver for coordinates/taps, debug server for diagnostics | Custom HTTP key server (new infrastructure, port conflicts, off-screen fragility) |
| Supabase verification | REST API via PowerShell | Automatable, exact field verification, scriptable cleanup | Supabase CLI (schema-only), Dashboard (not automatable) |
| Test data isolation | E2E prefix on existing account | Simple, no infrastructure overhead | Separate test company (complex), separate Supabase project (cost) |
| Credential storage | `.env.secret` separate from `.env` | Prevents mixing service role key with app anon key | Same `.env` file (exposure risk), env variable (less portable) |
| Flow registry location | `.claude/test_results/` | Persists in claude config repo, not gitignored with test_results/ | In `test_results/` (lost on gitignore), in project root (clutters) |
| Sync completion signal | Debug server `/sync/status` endpoint | Flutter app already POSTs to debug server; natural extension | Log polling (unreliable, no stable format), custom endpoint in app (new server) |
| Table names | Use actual schema names | Review caught 5 mismatches that would have caused 404s | Spec's original names (wrong) |
