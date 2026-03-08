# Sync-Aware Deletion System

**Date**: 2026-03-04
**Status**: APPROVED
**Branch**: fix/sync-dns-resilience

## Overview

**Problem**: Deleting any record (project, entry, contractor, etc.) only removes it from SQLite. The sync system blindly re-pulls it from Supabase, resurrecting it. There is no deletion awareness in the sync layer.

**Solution**: Hybrid soft-delete with 30-day trash.
- Add `deleted_at` and `deleted_by` columns to all synced tables (both SQLite and Supabase).
- Deleting a record sets `deleted_at = NOW()` instead of removing the row.
- All app queries filter `WHERE deleted_at IS NULL` so deleted records are invisible.
- Sync propagates `deleted_at` bidirectionally using the existing last-write-wins logic.
- Other team members (who have that project synced) see a notification ("Project X deleted by John") on next sync, then the record disappears from their view.
- A Trash screen lets users browse and restore deleted items within 30 days.
- A background purge job hard-deletes records where `deleted_at` is older than 30 days.
- **Conflict rule**: If a record is edited after it was deleted (by a different user offline), the edit wins — `deleted_at` is cleared, the record is restored.

**Success Criteria**:
- Deleted projects stay deleted after sync
- Deleted items appear in Trash for 30 days with Restore option
- Team members who have synced the project are notified of deletions by others
- Records purged after 30 days from both SQLite and Supabase

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | All 14 synced tables | Any record at any level can be independently deleted |
| Mechanism | Soft-delete + 30-day purge | Recoverable short-term, clean long-term |
| Multi-user notification | Notify then remove | Only for team members who have synced that project |
| Conflict resolution | Edit wins (resurrect) | If `updated_at > deleted_at`, clear deletion — preserves work |
| Trash UI | Visible Trash screen in Settings | Browse, restore, or permanently delete items within 30 days |
| Confirmation UX | Single dialog ("Move to trash?") | Trash makes deletion recoverable, heavy confirmation unnecessary |

## Data Model

### Schema changes — add to every synced table (both SQLite and Supabase):

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `deleted_at` | TEXT (ISO 8601) | Yes | NULL = active, timestamp = soft-deleted |
| `deleted_by` | TEXT (UUID) | Yes | User ID who performed the delete |

### Tables affected (all 14 synced tables):
`projects`, `daily_entries`, `locations`, `contractors`, `equipment`, `bid_items`, `photos`, `personnel_types`, `entry_personnel`, `entry_equipment`, `entry_quantities`, `todo_items`, `form_responses`, `calculation_history`

### Cascade behavior:
- When a project is soft-deleted, all children are also soft-deleted (set `deleted_at` + `deleted_by` on all child rows) in a single transaction with the same timestamp.
- FK constraints stay for referential integrity, but the app handles cascade soft-deletes in the repository layer, not via SQL cascade triggers.

### Purge logic:
- `purgeDeletedRecords()` runs on app startup and after sync completes.
- Hard-deletes any row where `deleted_at < NOW() - 30 days`.
- Runs bottom-up (children first, then parents) to respect FK constraints.
- Supabase: a pg_cron scheduled function does the same server-side.

### Conflict resolution:
- If `updated_at > deleted_at` on a record during sync, clear `deleted_at` and `deleted_by` (edit wins, record is restored).

### Notification tracking — new SQLite-only table `deletion_notifications`:

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | UUID |
| record_id | TEXT | ID of deleted record |
| table_name | TEXT | Which table |
| project_id | TEXT | Parent project (for scoping notifications) |
| record_name | TEXT | Display name of deleted item |
| deleted_by | TEXT | User who deleted |
| deleted_by_name | TEXT | Display name of user who deleted |
| deleted_at | TEXT | When |
| seen | INTEGER | 0/1 — dismissed by user |

## Sync Flow

### Push phase:
- Soft-deleted records push like any other update — `deleted_at` and `deleted_by` are regular columns that sync via the existing `updated_at` last-write-wins mechanism.
- No separate `queueOperation('delete')` needed.

### Pull phase (`_upsertLocalRecords` changes):
1. Remote record has `deleted_at` set, local record exists:
   - If local `updated_at > remote deleted_at` → **edit wins** → push local version back, clearing `deleted_at`
   - Otherwise → apply soft-delete locally, create `deletion_notification` if `deleted_by != current_user` AND user has project synced
2. Remote record has `deleted_at` set, local record does NOT exist:
   - **Skip it** — don't insert a deleted record
3. Remote record has no `deleted_at`, local record does not exist:
   - Insert as normal (new record)

### Post-sync:
- Run `purgeExpired()` to hard-delete rows older than 30 days.

## UI Changes

### Delete action update (all existing delete buttons):
- Set `deleted_at` and `deleted_by` instead of hard delete
- For project deletes: cascade soft-delete to all children in single transaction
- Show snackbar: "Moved to trash"
- Replace project double-confirmation with single dialog: "Move to trash? This project and all its contents will be permanently deleted after 30 days."

### Trash screen (Settings → Trash):
- Show item count badge on Settings row
- Grouped by type: Projects, Entries, Contractors, etc.
- Each item shows: name, deleted date, "deleted by [user]", days remaining
- Actions per item: Restore, Delete Forever
- "Empty Trash" button to purge everything
- Items within 3 days of expiry shown with warning indicator

### Deletion notifications:
- On sync, if `deletion_notifications` has unseen rows:
  - Banner/snackbar: "[User] deleted [Project Name]" (or "[User] deleted [N] items from [Project Name]")
  - Tap opens Trash filtered to those items
  - Dismiss marks `seen = 1`
- Only shown for projects the user has synced (scoped by project existence in local SQLite before sync)

### Restore cascades upward:
- Restoring a child whose parent is deleted → auto-restore parent too
- Toast: "Also restored Project X"

## Edge Cases

### Offline delete + offline edit conflict
- User A soft-deletes project. User B edits an entry in that project. Both offline, both sync later.
- Entry edit has `updated_at > deleted_at` → entry restored → parent project also restored (upward cascade).

### Purge during extended offline
- Local purge uses `MAX(local_clock, last_sync_time)` as reference — never purge based solely on a device clock that hasn't synced in 30+ days.

### Delete Forever from Trash
- Hard-deletes locally immediately. Queues hard-delete to Supabase via `sync_queue` with operation `'purge'`.

### New team member syncs a project with trashed items
- Pull phase skips records with `deleted_at` set if they don't exist locally. New members never see trashed items.

---

## Implementation Phases

### Phase 0: Schema Migration (Backend + Database)
- Add `deleted_at TEXT` and `deleted_by TEXT` columns to all 14 synced tables in SQLite
- Bump DB version, write migration (`ALTER TABLE ... ADD COLUMN`)
- Supabase migration: add same columns to all remote tables
- Add index on `deleted_at` for every table (query performance)
- Create `deletion_notifications` SQLite-only table
- Supabase: create a `pg_cron` job to hard-delete rows where `deleted_at < NOW() - 30 days`
- **Agent**: `backend-supabase-agent` (Supabase migration) + `backend-data-layer-agent` (SQLite schema)
- **Verify**: `flutter test` passes, app launches, existing data untouched

### Phase 1: Repository Layer — Soft-Delete + Query Filtering
- Replace all `database.delete()` calls with `database.update()` setting `deleted_at` + `deleted_by`
- Add cascade soft-delete method: given a project ID, soft-delete all children in one transaction
- Add `WHERE deleted_at IS NULL` filter to every query in `GenericLocalDatasource` and any custom queries
- Add `restore(id)` method: clears `deleted_at` + `deleted_by`, with upward cascade (restore parent if needed)
- Add `purgeExpired()` method: hard-deletes rows older than 30 days, child-first order
- **Agent**: `backend-data-layer-agent`
- **Verify**: Unit tests — delete sets `deleted_at`, queries exclude deleted rows, restore clears it, purge removes old rows

### Phase 2: Sync Layer — Deletion-Aware Sync
- Modify `_upsertLocalRecords()`: skip inserting records with `deleted_at` set if they don't exist locally
- Add edit-wins logic: if local `updated_at > remote deleted_at`, clear `deleted_at` and push back
- Add parent resurrection: if a child is restored by edit-wins, walk up and restore parent
- Add notification creation: when a remote soft-delete arrives from a different user on a synced project, insert `deletion_notification`
- Run `purgeExpired()` after sync completes
- **Agent**: `backend-data-layer-agent` + `backend-supabase-agent`
- **Verify**: Integration tests — delete locally → sync → stays deleted. Delete remotely → sync → deleted locally. Edit-wins conflict resolves correctly.

### Phase 3: UI — Delete Actions + Trash Screen + Notifications
- Update all delete buttons/actions to call soft-delete instead of hard-delete
- Replace project double-confirmation with single "Move to trash?" dialog
- Build Trash screen (Settings → Trash): grouped list, restore button, delete-forever button, empty-trash button
- Build deletion notification banner: shown on sync when `deletion_notifications` has unseen rows
- Wire up "Delete Forever" to hard-delete + sync queue purge operation
- **Agent**: `frontend-flutter-specialist-agent`
- **Verify**: Manual testing + widget tests for Trash screen

### Phase 4: Review + Hardening
- Code review via `code-review-agent`
- Security audit via `security-agent` (RLS policies must filter `deleted_at IS NULL` for API queries)
- Supabase RLS update: add `deleted_at IS NULL` to all SELECT policies so deleted records aren't visible via API
- Run `flutter test` full suite
- **Verify**: All tests green, security audit passes, no resurrection on sync
