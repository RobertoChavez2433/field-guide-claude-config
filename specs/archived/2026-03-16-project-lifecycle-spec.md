# Spec: Project Lifecycle Management + Logger Migration (PR2)

> **For Claude:** Use `/writing-plans` to create the implementation plan from this spec.

**Date**: 2026-03-16
**Status**: APPROVED (adversarial review complete, all findings addressed)
**Delivery**: 2 PRs — PR1 (project lifecycle + schema), PR2 (logger migration)
**Reviews**: `.claude/adversarial_reviews/2026-03-16-project-lifecycle/`

---

## 1. Overview

### Problem

The Projects tab only shows projects in local SQLite. Projects created by teammates in Supabase are invisible unless the user navigates to Settings → Manage Synced Projects, which only toggles enrollment without triggering sync. The import/delete experience has no clear path, no warnings, and no user control over what data lives on the device vs. the database. The sync system uses deprecated `DebugLogger` (30+ calls) instead of the structured `Logger` system, making sync errors extremely hard to debug. Accumulated unsynced data creates persistent junk with no visibility.

### Goals

1. Every company project visible in the Projects tab (metadata only, no heavy data auto-load).
2. Import a project's full data with one action + visible progress.
3. Remove project data from the device without deleting from Supabase.
4. Soft-delete from both device + Supabase with explicit confirmation and authorization.
5. All project lifecycle management happens from the Projects tab. Remove "Manage Synced Projects" from Settings (keep read-only view in Sync Dashboard).
6. Supabase is always the authoritative source of truth.
7. Sync health indicators on project cards + Sync Dashboard — unsynced data is always visible.
8. All logging (including sync) flows through the unified `Logger` system with two tiers: release (sanitized operations + errors) and debug (`DEBUG_SERVER=true` flag gives full unrestricted visibility).

### Success Criteria

- Company projects created by other users appear in the Projects tab within one sync cycle.
- Importing a project triggers child data sync and completes in the background.
- "Remove from device" removes all local child data while Supabase copy is untouched.
- "Delete from database" soft-deletes project + all children in both SQLite and Supabase.
- User sees clear warnings before destructive actions. Unsynced data is always visible via card indicators.
- RLS prevents unauthorized database deletions (new migration enforces owner/admin gate).
- Logger migration: zero `DebugLogger`/`AppLogger` imports remain.
- Release logs contain no PII (file transport scrubs `data:` maps in release mode). Debug flag gives unrestricted eyes.

---

## 2. Project Visibility

### Current Behavior

`ProjectListScreen` queries `SELECT * FROM projects WHERE deleted_at IS NULL` — local SQLite only. The `ProjectAdapter` (`ScopeType.direct`) pulls ALL company projects to SQLite on every sync, but only after a successful sync cycle.

### Design: Merged View in Projects Tab

The Projects tab shows three project states:

| State | Source | Card Display | Indicator |
|-------|--------|-------------|-----------|
| **Synced** (healthy) | SQLite + `synced_projects` | Full card — name, number, description, client, dates | Green check (synced) or orange cloud-upload (has pending changes) |
| **Remote only** | Supabase, not in SQLite | Metadata card — name, number, description | Grey cloud — "Not on device", import action available |
| **Unsynced/Local only** (error state) | SQLite, not backed up to Supabase | Full card with warning indicator | Red warning — prompt to sync/upload. Temporary condition. |

**Implementation**: On tab entry + pull-to-refresh, fetch `id, name, project_number, description, is_active` from Supabase for all company projects (with `deleted_at IS NULL` filter to exclude soft-deleted). Merge client-side with local SQLite records. Deduplicate by `id`.

**Unsynced/Local-only detection**: Project IDs present in SQLite but absent from the Supabase fetch result = local-only error state.

**No heavy data auto-loaded** — photos, entries, bid items only come via explicit Import action.

### Sync Health on Project Cards

Each project card shows a small sync status icon:
- **Green check** — fully synced, no pending changes
- **Orange cloud-upload** — has N unsynced local changes (count shown)
- **Red warning** — sync error / unable to sync
- **Grey cloud** — not on device (remote only)

Pending change count comes from `change_log` table queried by `project_id` column (see Section 12: Schema Changes).

**Performance**: Cache counts in a `ProjectSyncHealthProvider` (Map<String, int>), refreshed on sync completion — NOT on every card render. Counts stale between syncs are acceptable.

---

## 3. Import Flow

### Trigger

User taps a remote-only project card → "Import to Device" action.

### Steps

1. **Check network**: If offline, block: "Internet connection required to import."
2. **Enroll**: `INSERT INTO synced_projects (project_id, synced_at) VALUES (?, now())` with `ConflictAlgorithm.ignore`.
3. **Trigger sync**: Call `SyncOrchestrator.syncLocalAgencyProjects()` immediately (not waiting for background cycle). The engine reads `synced_projects` and will pull child data for the newly enrolled project. **(Interim approach — see Section 13: Future Work for targeted `syncProject()` method.)**
4. **Progress feedback**: New `ProjectImportBanner` widget + `ProjectImportRunner extends ChangeNotifier` — independent from the PDF `ExtractionBanner`. Shows "Importing [Project Name]..." with record count progress.
5. **User stays on Projects list** while import runs in background.
6. **On completion**: Banner turns green. Project transitions to "Synced" state.
7. **On failure**: Toast "Import failed — will retry on next sync." Enrollment row persists — next sync cycle continues.

### Notes

- Import is idempotent (upsert on `synced_projects`).
- If sync is already running, enrollment is set and the next sync cycle picks it up.
- Import writes NO Supabase records — pure local enrollment.
- Guard against concurrent import: if sync is already running for this project, show "Sync in progress" instead of starting another.

---

## 4. Delete Flows

### Entry Point

Long-press project card or three-dot menu → "Delete". Bottom sheet appears.

### Delete Options Bottom Sheet

```
┌─────────────────────────────────────┐
│  Remove "Springfield DWSRF"         │
│                                     │
│  ☐ Remove from this device          │
│    Removes all local data (entries, │
│    photos, bid items). Database     │
│    copy is untouched.               │
│                                     │
│  ☐ Delete from database             │
│    Permanently soft-deletes for all │
│    team members. Recoverable for    │
│    30 days in Trash.                │
│                                     │
│  [Cancel]              [Confirm]    │
└─────────────────────────────────────┘
```

**Rules:**
- Checking "Delete from database" auto-checks "Remove from device" (can't keep local copy of deleted remote data).
- At least one checkbox must be selected before Confirm is enabled.
- "Delete from database" requires authorization (owner or admin). If unauthorized, checkbox is grayed out: "Only the project owner can delete from database."
- If `created_by_user_id` is NULL (legacy project): treat as admin-only access (most conservative).
- Confirm button label changes: "Remove from Device" (device only) or "Delete Project" (database, red).

### 4A: Remove from Device Only

1. If unsynced changes exist: show inline warning "This project has N unsynced changes" (non-blocking — user already sees the orange card indicator).
2. **Clean up change_log**: `DELETE FROM change_log WHERE project_id = ? AND processed = 0` — prevents data resurrection on next sync push.
3. **Clean up conflict_log**: `DELETE FROM conflict_log WHERE record_id IN (...)` for all affected record IDs.
4. Hard-delete all local child rows (entries, photos, bid items, all `viaProject` tables).
5. **Clean up local photo files**: Queue deletion of files referenced by `photos.file_path` before deleting the rows.
6. Hard-delete local project row from SQLite.
7. Remove `synced_projects` row.
8. Project now appears as "Remote only" (grey cloud) if Supabase copy exists.

### 4B: Delete from Database

1. Authorization check: `created_by_user_id == auth.uid()` OR company admin. Block if unauthorized. NULL `created_by_user_id` → admin-only.
2. Final confirmation dialog: "This will delete [Project Name] for all team members. Recoverable from Trash for 30 days."
3. `SoftDeleteService.cascadeSoftDeleteProject(projectId)` — sets `deleted_at` on project + all children.
4. Remove `synced_projects` row.
5. Clean up `change_log` and `conflict_log` for this project.
6. Next sync push → Supabase receives soft-deleted records.
7. `stamp_deleted_by()` trigger enforces `deleted_by = auth.uid()`.
8. Project disappears for all team members on their next sync.

### 4C: Both Checked

Execute 4B (which includes local cleanup). The soft-delete cascade handles both local and remote.

---

## 5. Data Health & Transparency

### Always-Visible Sync Status

Sync health is NOT just a delete-time warning. It's an always-on system:

1. **Project card indicators**: Every project card shows sync status icon (green/orange/red/grey — see Section 2).
2. **Unsynced changes count**: Orange indicator includes count of pending changes from `change_log WHERE project_id = ?`.
3. **Unsynced/Local-only error state**: Projects in SQLite but not backed up to Supabase show a red warning. Tapping explains the sync status and offers "Sync Now."

### Delete-Time Warnings

| Scenario | Warning |
|----------|---------|
| Remove from device with unsynced changes | Inline: "N unsynced changes" (non-blocking) |
| Delete from database | Final confirmation dialog required |
| Both options | Both warnings |
| Offline + delete from database | "Cannot delete from database while offline." Disable that checkbox. |

### Cross-Device Behavior

`synced_projects` is a device-local table with no Supabase equivalent. Removing a project from device A does NOT affect device B (which still has its own enrollment row and child data). This is expected behavior — each device manages its own local data independently.

---

## 6. Settings Changes

**Remove "Manage Synced Projects" tile from Settings.** All project lifecycle management happens from the Projects tab.

**Keep `ProjectSelectionScreen` accessible from Sync Dashboard** as a read-only advanced view (no toggle actions — view enrollment status only).

**Three locations to update:**
1. `lib/features/settings/presentation/screens/settings_screen.dart:199-202` — Remove tile
2. `lib/features/sync/presentation/screens/sync_dashboard_screen.dart:263-265` — Keep link, make screen read-only
3. `lib/core/router/app_router.dart:616-618` — Keep route registration (still needed for Sync Dashboard link)

---

## 7. Data Flow

### Enrollment Gate

```
synced_projects table: (project_id TEXT PK, synced_at TEXT)

Controls which projects' child data the sync engine pulls.
- Adding a row → next sync pulls children
- Removing a row → next sync stops pulling children
- Project table itself (ScopeType.direct) always pulls ALL company projects
```

### Import Data Flow

```
User taps Import
  → INSERT INTO synced_projects
  → SyncOrchestrator.syncLocalAgencyProjects()  ← immediate trigger
    → Engine reads synced_projects, pulls children for enrolled projects
    → ProjectImportRunner emits progress to ProjectImportBanner
  → Banner completes → project is "Synced"
```

### Remove from Device Data Flow

```
User confirms Remove from Device
  → DELETE FROM change_log WHERE project_id = ? AND processed = 0
  → DELETE FROM conflict_log WHERE record_id IN (affected IDs)
  → Delete local photo files from disk
  → Hard-DELETE all child rows (entries, photos, bid_items, etc.)
  → Hard-DELETE project row from SQLite
  → DELETE FROM synced_projects
  ← Project appears as "Remote only" in UI
```

### Delete from Database Data Flow

```
User confirms Delete from Database
  → Authorization check (created_by or admin; NULL = admin-only)
  → Clean change_log + conflict_log
  → SoftDeleteService.cascadeSoftDeleteProject()
    → UPDATE SET deleted_at on project + all children
  → DELETE FROM synced_projects
  → Next sync push → Supabase receives soft-deletes
  → stamp_deleted_by() trigger enforces attribution
  ← Project disappears for all team members
```

---

## 8. PR2: Logger Migration

Carried from `2026-03-15-pipeline-ux-overhaul-spec.md` PR2 scope. The entire app should flow through the unified `Logger` system, designed with the systematic debugging skill as the primary source of debug information.

### How Logger Already Works

The `Logger` class (`lib/core/logging/logger.dart`) already has:
- **Per-category log files**: `sync.log`, `pdf_import.log`, `ocr.log`, `database.log`, `auth.log`, `navigation.log`, `errors.log`, `ui.log`, `app_session.log`
- **Flat master log**: Single file that gets EVERYTHING regardless of category
- **HTTP transport**: Structured JSON to debug server (`tools/debug-server/server.js` on port 3947) when `DEBUG_SERVER=true`
- **`hypothesis()` method**: HTTP-only, for tagging debug hypotheses during systematic debugging sessions
- **PII scrubbing**: `_sensitiveKeys` blocklist + regex patterns for emails/JWTs (currently HTTP transport only)

### Two-Tier Logging Model

| Mode | Trigger | What gets logged | PII handling |
|------|---------|-----------------|-------------|
| **Release** (default) | Normal APK build | Operations + errors only. "Sync started", "Pulled 12 records from projects in 340ms", "Sync failed: DNS unreachable". | **File transport: release-only scrubbing on `data:` maps** (new — see 8A). HTTP transport: full scrubbing (existing). |
| **Debug** | `--dart-define=DEBUG_SERVER=true` | EVERYTHING. Full payloads, SQL queries, auth context, record content, conflict details, timing, hypothesis tags. | No scrubbing — unrestricted visibility for developer |

The `DEBUG_SERVER` flag is compile-time, can never accidentally ship in production. Debug server is localhost-only via ADB forwarding.

### 8A: Release-Safe File Logging (must run first)

**New: Add release-only scrubbing to the file transport.** In `_log()`, when `kReleaseMode == true`, apply `_scrubSensitive()` to `data:` maps before writing to category sinks. Debug builds keep full fidelity.

Additional changes:
- Construction-domain PII blocklist additions: `'project_name', 'contractor_name', 'location_name', 'site_address'` plus `_endsWith` variants (`_address`, `_location`).
- Fix HTTP transport: run `_scrubSensitive()` before truncation check.
- Log retention: delete session folders older than 14 days. Cap at 50MB total.

**This step must complete before 8B–8E begin.**

### 8B: Migrate 22 DebugLogger Files → Logger

Mechanical replacement. `DebugLogger.*()` → `Logger.*()` with structured `data:` parameters.

**Sync (6 — critical for sync debugging):** `sync_engine.dart`, `sync_orchestrator.dart`, `sync_lifecycle_manager.dart`, `change_tracker.dart`, `orphan_scanner.dart`, `integrity_checker.dart`
- Add structured data: `Logger.sync('Pulled records', data: {'table': 'projects', 'count': 12, 'durationMs': 340})`
- Add `Logger.hypothesis()` at critical sync decision points (DNS checks, adapter selection, push/pull boundaries, conflict resolution, error classification)
- **Caller discipline**: `data:` maps must NOT contain domain entities (project names, contractor names, entry content). Use IDs and counts only. Release scrubbing is a safety net, not a substitute.

**PDF (5):** `extraction_pipeline.dart`, `post_processor_v2.dart`, `pdf_import_service.dart`, `pdf_import_helper.dart`, `grid_line_remover.dart`

**Database (2):** `database_service.dart`, `schema_verifier.dart`

**Services (3):** `soft_delete_service.dart`, `startup_cleanup_service.dart`, `storage_cleanup.dart`

**Projects (2):** `project_repository.dart`, `project_local_datasource.dart`

**Quantities (2):** `bid_item_provider.dart`, `budget_sanity_checker.dart`

**Shared (1):** `generic_local_datasource.dart`

### 8C: Migrate ~47 debugPrint Files → Logger

Replace `debugPrint()` with appropriate `Logger` category calls.

### 8D: Add Logging to 16 Dark Pipeline Stages

Per-page OCR timing + memory snapshots at key extraction points.

### 8E: Delete Deprecated Wrappers

- Delete `lib/core/logging/debug_logger.dart`
- Delete `lib/core/logging/app_logger.dart`
- Remove all imports app-wide.
- Verify: `grep "DebugLogger\|AppLogger" lib/` returns zero results.

---

## 9. Edge Cases

| Scenario | Behavior |
|----------|----------|
| Import while offline | Block: "Internet connection required." |
| Remove from device while offline | Allowed (local only). |
| Delete from database while offline | Block: "Internet connection required." Disable checkbox. |
| Concurrent delete by two users | LWW on `deleted_at`. Same outcome. |
| User A imports while User B deletes | A's import completes. Next sync pulls `deleted_at`, app removes locally + shows toast. |
| Partial import failure (network drop) | `synced_projects` row persists. Next sync resumes. |
| Large projects (thousands of entries) | May take multiple sync cycles. Banner dismisses after first cycle. |
| Import already-enrolled project | No-op (upsert). |
| Unsynced local-only project (error state) | Red warning on card. Prompt to sync. |
| Remove from device on one device, same account on another | Device B unaffected — `synced_projects` is device-local. Documented behavior. |
| Legacy project with NULL `created_by_user_id` | Admin-only delete from database. |

---

## 10. Security

- **View**: RLS limits to user's `company_id`.
- **Import**: Local enrollment only. No Supabase writes. No new RLS policy needed.
- **Database delete**: Client-side owner/admin check (UX guard) + **new Supabase RLS migration** (hard enforcement — see Section 12). `stamp_deleted_by()` trigger prevents attribution spoofing.
- **Remove from device**: Pure local operation. No Supabase permission required.
- **Metadata fetch**: Only non-sensitive fields (`id, name, project_number, description, is_active`). Supabase query includes `deleted_at IS NULL` filter.
- **Logger**: Release builds scrub `data:` maps via `_scrubSensitive()` in file transport (new). Debug mode is compile-time gated, can't ship to users.
- **Data resurrection prevention**: `change_log` and `conflict_log` cleaned before device removal to prevent ghost sync pushes.

---

## 11. Testing Strategy

### Unit Tests
- `ProjectListProvider` merges local + remote projects correctly
- Import: `synced_projects` upsert + sync trigger called
- Remove from device: all child tables cleared + `change_log`/`conflict_log` cleaned + photo files deleted
- Delete from database: authorization check blocks non-owners; NULL `created_by_user_id` → admin-only
- Sync health indicators: pending count query via `change_log.project_id` correct
- `ProjectImportRunner` state machine (idle → running → complete/error)

### Widget Tests
- Projects tab shows three project states (synced, remote, unsynced)
- Delete bottom sheet: checkbox rules, confirm button state, authorization gate
- Sync status icons render correctly per state
- `ProjectImportBanner` renders progress correctly

### Integration Tests
- Full import flow: enroll → sync → data appears
- Remove from device: SQLite empty, Supabase untouched, no data resurrection on next sync
- Delete from database: soft-delete propagates on sync
- Logger: release build logs contain no PII in `data:` maps

### Logger Migration Verification
- `grep "DebugLogger\|AppLogger" lib/` → zero results
- `grep "debugPrint" lib/` → zero results (except `_originalDebugPrint` in Logger itself)

---

## 12. Schema Changes (from adversarial review)

### Migration: Add `project_id` to `change_log`

**Why**: Per-project unsynced change counts (Section 2, 5) and device-removal cleanup (Section 4A) require filtering `change_log` by project. The current schema has no `project_id` column.

```sql
ALTER TABLE change_log ADD COLUMN project_id TEXT;
CREATE INDEX idx_change_log_project_id ON change_log(project_id);
```

Update all `change_log` triggers (`sync_engine_tables.dart:126-152`) to populate `project_id` for project-scoped tables. Tables without a direct `project_id` (e.g., `equipment` via contractor) leave it NULL.

Backfill existing rows: `UPDATE change_log SET project_id = (SELECT project_id FROM daily_entries WHERE id = change_log.record_id) WHERE table_name = 'daily_entries'` (repeat for each table).

### Migration: Tighten RLS for Project Soft-Delete

**Why**: Current `company_projects_update` policy allows any non-viewer to soft-delete any project. The spec requires owner/admin enforcement.

```sql
DROP POLICY IF EXISTS "company_projects_update" ON projects;

CREATE POLICY "company_projects_update" ON projects
  FOR UPDATE TO authenticated
  USING (company_id = get_my_company_id() AND NOT is_viewer())
  WITH CHECK (
    CASE
      WHEN deleted_at IS NOT NULL AND (SELECT deleted_at FROM projects WHERE id = projects.id) IS NULL THEN
        created_by_user_id = auth.uid() OR is_approved_admin()
      ELSE true
    END
  );
```

This restricts the `deleted_at` NULL→non-NULL transition to owner or admin while allowing all other UPDATE operations for any non-viewer.

---

## 13. Future Work (out of scope for this spec)

- **Targeted `SyncEngine.syncProject(projectId)`**: A scoped sync method that pulls only one project's children. Currently the import uses the full `syncLocalAgencyProjects()` as an interim approach. A separate plan should design the targeted sync path for better import UX and efficiency.
- **Sync Dashboard "Data Health" section**: Per-project last-sync-time and detailed health view. Requires new `sync_metadata` keyed by project_id or a new table. Deferred to follow-up spec.
- **Orphaned data detection + cleanup**: `OrphanScanner` already exists but isn't surfaced in UI. Deferred.
- **`synced_projects` cross-device sync**: Currently device-local only. A Supabase `user_project_enrollment` table could persist enrollment across devices. Deferred.

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Settings "Manage Synced Projects" | Remove from Settings, keep read-only in Sync Dashboard | Projects tab is primary, Dashboard is advanced view |
| Remote metadata fetch timing | On tab entry + pull-to-refresh | Simple, predictable, one Supabase request |
| Post-import navigation | Stay on Projects list | Import runs in background, user can browse |
| Delete UX | Two checkboxes in bottom sheet | Clear, explicit, covers all cases |
| Unsynced data visibility | Card indicators (cached in provider) | Always-visible, not per-render |
| Logging tiers | Release (file-scrubbed) + Debug (everything) | Existing Logger infrastructure, DEBUG_SERVER flag |
| Local-only project state | Error state with warning | Prompts user to sync, prevents data loss |
| `change_log` schema | Add `project_id` column via migration | Enables per-project unsynced counts and device-removal cleanup |
| Import sync method | Interim: full `syncLocalAgencyProjects()` | Works today. Targeted sync is future work. |
| Import progress UI | New `ProjectImportBanner` + `ProjectImportRunner` | Independent from PDF banner. Clean feature boundary. |
| RLS soft-delete gate | New migration: tighten UPDATE policy | Security is non-negotiable per CLAUDE.md HARD CONSTRAINT |
| NULL `created_by_user_id` | Admin-only delete | Most conservative for legacy projects |
| File transport PII | Release-only `_scrubSensitive()` on `data:` maps | Best of both worlds: debug fidelity + release safety |
| `client_name` in metadata fetch | Dropped | Commercial PII not needed for project card display |
| Device removal cleanup | Clear `change_log` + `conflict_log` + photo files | Prevents data resurrection and orphaned files |

---

## Adversarial Review Summary

**Code Review**: 5 MUST-FIX (all addressed above: M1 change_log schema, M2 targeted sync, M3 banner independence, M4 RLS gap, M5 cleanup scope)

**Security Review**: 3 MUST-FIX (MF-1 RLS = M4 above, MF-2 data resurrection = addressed in Section 4A, MF-3 entry_personnel = FALSE FINDING — table doesn't exist, only `entry_personnel_counts` which is already in cascade)

All SHOULD-CONSIDER items addressed: cached counts (S1), nullable `created_by_user_id` (S2), photo file cleanup (S3), Sync Dashboard deferred (S4), `client_name` dropped (SC-1), file transport scrubbing (SC-2), cross-device documented (SC-3), `conflict_log` cleanup (SC-4).
