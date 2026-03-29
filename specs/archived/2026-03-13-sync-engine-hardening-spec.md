# Sync Engine Hardening Spec

> **For Claude:** Use `/writing-plans` to create the implementation plan from this spec.

**Date**: 2026-03-13
**Scope**: 16 fixes (4 CRITICAL, 6 HIGH, 4 MEDIUM, 1 LOW, 1 UI)
**Estimated Files**: ~20
**Blockers Resolved**: BLOCKER-24 (duplicate key), BLOCKER-29 (deleted data resurrects)
**Reviews**: code-review-agent (APPROVE w/ findings), security-agent (APPROVE w/ findings)

---

## 1. Overview

### Purpose
Comprehensive sync engine hardening to fix 2 active blockers (BLOCKER-24: duplicate key on projects, BLOCKER-29: deleted data resurrects after sync), 4 critical data integrity bugs, 9 robustness improvements, and 1 admin UI fix (join request display shows name/email instead of truncated UUID).

### Scope
**Included**: Push flow (soft-delete, upsert pre-check, company_id validation, error categorization, photo cleanup), pull flow (conflict resolution, integrity checker, trigger suppression), change tracker (circuit breaker, FK blocking), SQLite schema alignment, orphan cleanup, admin dashboard join request display, Supabase RLS tightening + triggers.

**Excluded**: Realtime subscriptions, full sync engine rewrite/architecture change, EXIF/HEIC stripping (deferred), dedup improvements (deferred), empty-project-list edge case (deferred), pull cursor redesign (review found removing safety margin creates data loss risk — keeping existing behavior).

### Success Criteria
- Sync completes without `duplicate key` errors on projects and constrained tables
- Locally deleted records stay deleted after sync (no resurrection)
- Admin dashboard shows requester name + email
- No silent data loss during conflict resolution
- Error categorization visible in sync logs
- Orphaned storage files auto-cleaned after 24h
- `deleted_by` cannot be spoofed (server-side trigger enforces `auth.uid()`)

---

## 2. Data Model

### 2.1 SQLite Schema Changes — UNIQUE Constraints

**Review finding (MF-1)**: Original spec listed 6 tables. Code review found:
- `projects`, `entry_contractors`, `user_certifications` — **already have** the UNIQUE constraint in SQLite
- `form_field_registry`, `form_field_mapping_cache` — **tables don't exist** (dropped/never created)
- `personnel_type_registry` — wrong name, actual table is `personnel_types`

**Corrected**: Only `personnel_types(project_id, semantic_name)` needs verification. If it doesn't have the constraint, add it. The migration dedup pass applies only to this table.

| Table | Status | Action |
|-------|--------|--------|
| `projects` | Already has `UNIQUE(company_id, project_number)` | Pre-check only (no schema change) |
| `entry_contractors` | Already has `UNIQUE(entry_id, contractor_id)` | Pre-check only |
| `user_certifications` | Already has `UNIQUE(user_id, cert_type)` | Pre-check only |
| `personnel_types` | Needs verification | Add UNIQUE if missing |
| `form_field_registry` | Table dropped | Skip |
| `form_field_mapping_cache` | Table doesn't exist | Skip |

### 2.2 Supabase — New RPC + Triggers + RLS Fixes

**New RPC**: `get_pending_requests_with_profiles(p_company_id UUID)` — `SECURITY DEFINER` function. Joins `company_join_requests` with `user_profiles` on `user_id`. Returns: `id`, `user_id`, `company_id`, `status`, `requested_at`, `display_name`, `email`. Guarded by `is_approved_admin()` + company match.

**New trigger (MF-5)**: `stamp_deleted_by()` — When `deleted_at` changes from NULL to non-NULL, force `deleted_by = auth.uid()`. Applied to all 16 synced tables. Prevents spoofing deletion attribution.

```sql
CREATE OR REPLACE FUNCTION stamp_deleted_by()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
    NEW.deleted_by = auth.uid();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
```

**RLS fix (SC-3)**: Update `view_own_request` policy on `company_join_requests` to use `is_approved_admin()` instead of just `role = 'admin'`. Prevents deactivated admins from seeing join requests.

**Email backfill (SC-4)**: One-time migration to populate `user_profiles.email` from `auth.users.email` where NULL.

### 2.3 CompanyJoinRequest Model

Add two nullable fields: `displayName` (String?) and `email` (String?). Update `fromJson` to parse `display_name` and `email` from the RPC response. Fields are null when fetched via direct table query.

### 2.4 Soft-Delete Design (Local + Remote)

**Review finding (MF-2)**: Resolved as **Option A — soft-delete locally too**.

- App sets `deleted_at` on local SQLite row (UPDATE, not DELETE)
- SQLite UPDATE trigger fires → change_log `operation='update'`
- Push recognizes records where `deleted_at` was set (changed from NULL to non-NULL) and sends `.update({'deleted_at': timestamp, 'deleted_by': userId})` to Supabase
- Pull respects `deleted_at` — if pulled record has `deleted_at` set, soft-delete locally
- All local queries filter by `WHERE deleted_at IS NULL`
- The `stamp_deleted_by()` server trigger enforces `deleted_by = auth.uid()` regardless of what the client sends

**Detection**: The push logic must detect "this update is a soft-delete" vs "this update is a normal edit." Strategy: compare old vs new `deleted_at` in the change_log payload. If `deleted_at` changed from NULL → non-NULL, treat as soft-delete push. Otherwise, normal upsert.

---

## 3. Sync Engine Behavior Changes

### Push Flow

#### 3A. Soft-Delete Push (Issue 1 — CRITICAL)
- When pushing a change_log `operation='update'` where the local record's `deleted_at` is non-NULL, send `.update({'deleted_at': timestamp, 'deleted_by': userId}).eq('id', recordId)` instead of full upsert
- For photo records, also mark the storage file for orphan cleanup
- Server-side `stamp_deleted_by()` trigger enforces `deleted_by = auth.uid()`

#### 3B. Upsert Pre-Check (Issues 2, 3 — CRITICAL/HIGH)
- Before pushing a record for a table with compound UNIQUE constraint, query Supabase for existing match on the natural key columns
- Same ID → normal upsert (update existing row)
- Different ID → mark failed with clear message: `'Project number already exists on server (created by another device)'`
- No match → normal upsert (insert new row)
- Applies to: `projects(company_id, project_number)`, `entry_contractors(entry_id, contractor_id)`, `user_certifications(user_id, cert_type)`, `personnel_types(project_id, semantic_name)` if constrained
- **TOCTOU safety net (MF-4)**: If pre-check passes but upsert hits `23505`, treat as **retryable** (another device inserted between check and push). Re-run pre-check on next cycle.
- **Pre-check is a UX optimization, NOT a security boundary (SC-5)**. The Supabase UNIQUE constraint + 23505 error categorization is the actual integrity guarantee.

#### 3C. Company ID Validation (Issue 4 — CRITICAL)
- Before pushing any record **that has a `company_id` column** (currently just `projects`), validate `record['company_id'] == currentUserCompanyId`
- Tables scoped via `project_id` or `entry_id` (all other synced tables) are indirectly validated by their parent's company_id
- Mismatch → logged as `'Rejected: company_id mismatch'`, marked failed, not retried
- Null company_id → stamped with current user's company (existing behavior)

#### 3D. Photo Cleanup on Partial Failure (Issue 5 — CRITICAL)
- If Phase 2 (metadata upsert) fails after Phase 1 (file upload), attempt to delete uploaded file from storage
- If cleanup fails, log it — orphan scanner catches it later

#### 3E. Error Categorization (Issue 19 — LOW)
- Parse `PostgrestException.code`:
  - `23505` → "Constraint violation" (duplicate key) — **retryable** if pre-check was clean (TOCTOU)
  - `42501` → "RLS denied" — permanent
  - `23503` → "FK violation" (parent missing) — permanent
  - `401/403` → "Auth expired" — refresh token, retry
  - `429/503` → "Rate limited" — retry with backoff
  - Network errors → "Network" — retry
- Only retry transient errors. Mark permanent errors as failed immediately.

### Pull Flow

#### 3F. Soft-Delete Pull (Issue 1, continued)
- When pulling a record where `deleted_at IS NOT NULL`, set `deleted_at` locally (with trigger suppression to avoid re-pushing)
- If record doesn't exist locally, skip
- Pull query includes soft-deleted records (no `WHERE deleted_at IS NULL` filter on pull)

#### 3G. Conflict Resolution Race Fix (Issue 6 — CRITICAL)
- When local wins a conflict and a manual change_log entry is inserted, snapshot the record's current `updated_at` in the change_log metadata
- When pushing that entry later, re-read the local record. If `updated_at` is newer than the snapshot, use the current version (user edited after conflict). If same, use the conflict-winning version.

#### 3H. Pull Cursor — KEEP EXISTING (Review Override)
**Review finding (MF-3)**: The 5-second safety margin at `sync_engine.dart:699` exists to handle Supabase transaction commit skew. Removing it creates a data loss window. **Keep the existing `gte` + 5-second margin.** Rely on timestamp-equality dedup at `sync_engine.dart:746` to handle overlap.

No code change for this section.

#### 3I. Null Timestamp Conflict (Issue 15 — MEDIUM)
- Null remote + valid local → local wins
- Null local + valid remote → remote wins
- Both null → remote wins (safety default)

### Infrastructure

#### 3J. Concurrent Sync Mutex Fix (Issue 11 — HIGH)
- Increase stale timeout from 5 to 15 minutes
- Add `last_heartbeat` column to `sync_lock` table
- Sync updates `last_heartbeat` every 60 seconds during operation
- Stale check uses heartbeat: if `last_heartbeat` > 2 minutes ago, consider stale

#### 3K. Integrity Checker — Max Reset Guard (Issue 12 — MEDIUM)
- Track consecutive cursor resets per table (in memory, reset on successful pull)
- After 3 consecutive resets for the same table, stop resetting and log diagnostic: `'Integrity check failed 3 times for [table] — possible RLS misconfiguration'`
- Surface via `SyncProvider` state for sync dashboard display

#### 3L. Change Tracker Circuit Breaker (Issue 9 — HIGH)
- If change_log exceeds 1000 entries, set `SyncStatus.circuitBreakerTripped`
- Sync dashboard shows a dismissable banner: "Sync paused: unusually high number of pending changes"
- User dismisses → calls `ChangeTracker.resetCircuitBreaker()` → resumes sync
- Auto-purge: entries older than 7 days with 3+ retries are deleted automatically
- Circuit breaker threshold should be configurable via `SyncEngineConfig`

#### 3M. FK Pre-Check — Per-Record Blocking (Issue 14 — MEDIUM)
- For each child change, look up its parent FK value in the change_log
- If the specific parent record synced successfully (or has no pending changes), allow the child to push
- Only block children whose specific parent record has failed
- Increases per-record DB queries but unblocks healthy children when only some parents fail

#### 3N. Cursor Reset Tolerance (Issue 20 — MEDIUM)
- Only reset cursor if count difference exceeds `max(5, 10% of expected count)`
- Below threshold: log drift but don't reset
- Prevents bandwidth waste from normal concurrent-operation variation

#### 3O. Orphan Auto-Cleanup (Issue 13 — MEDIUM)
- Modify existing `OrphanScanner` to accept a `autoDelete` flag
- When enabled: files >24h old with no matching DB row are deleted from storage
- Cap at 50 deletions per sync cycle to avoid timeout
- Log each deletion with full storage path and file age for audit
- Runs after photo sync completes

---

## 4. Admin Dashboard — Join Request Display (Issue 21)

### Supabase RPC
New `get_pending_requests_with_profiles(p_company_id UUID)`:
- `SECURITY DEFINER` + `SET search_path = public` + `STABLE`
- Validates `is_approved_admin()` + company match
- Joins `company_join_requests` with `user_profiles` on `user_id`
- Returns: `id`, `user_id`, `company_id`, `status`, `requested_at`, `display_name`, `email`
- `REVOKE FROM anon`, `GRANT TO authenticated`

### Repository Change
`AdminRepository.getPendingJoinRequests()` calls `.rpc('get_pending_requests_with_profiles', params: {'p_company_id': companyId})` instead of direct table query.

**Review finding (MF-6)**: Replace `assert(companyId != null)` with `if (companyId == null) throw StateError(...)` in all 6 locations in `admin_repository.dart`. `assert()` is stripped in release builds.

### UI Change
`_buildRequestTile()` shows `displayName` and `email` instead of truncated UUID. Avatar shows initials from `displayName`.

---

## 5. Edge Cases

### Soft-Delete
| Scenario | Handling |
|----------|----------|
| Record already deleted on server | UPDATE sets deleted_at again — no-op. No error. |
| Pull soft-deleted record never local | Skip. |
| Local delete vs remote edit conflict | Timestamp comparison. Newer wins. If remote edit is newer, un-soft-delete locally. |
| Delete project with children | Push project soft-delete. Children remain until explicitly deleted. |
| Old client hard-deletes remotely | Record disappears from remote. Pull side treats missing record as deleted locally. |
| Detect soft-delete vs normal edit | Compare local record's deleted_at: NULL→non-NULL = soft-delete push. Otherwise = normal upsert. |

### Pre-Check
| Scenario | Handling |
|----------|----------|
| Pre-check query fails (network) | Transient error. Retry next cycle. Don't push. |
| Match deleted between pre-check and upsert | Upsert succeeds normally. |
| Two devices push same project simultaneously | First wins. Second hits 23505 → retryable. Next cycle pre-check catches it with clear message. |
| TOCTOU: pre-check clean, upsert hits 23505 | Treat as retryable. Re-run pre-check next cycle. |

### Circuit Breaker
| Scenario | Handling |
|----------|----------|
| Legitimate bulk import (500+) | User dismisses banner, forces continue. |
| Poisoned change_log | Circuit breaker pauses. Auto-purge cleans entries >7 days with 3+ retries. |
| Background sync with circuit breaker tripped | Background sync also respects the pause. Only user dismissal resumes. |

### Photo Cleanup
| Scenario | Handling |
|----------|----------|
| File being uploaded by concurrent sync | 24h age threshold prevents premature deletion. |
| Storage API rate-limited | Stop cleanup this cycle. Resume next. |
| >50 orphans | Delete oldest 50. Rest caught in subsequent cycles. |

### Mutex
| Scenario | Handling |
|----------|----------|
| App killed mid-sync | 15-minute stale timeout releases lock. |
| Sync takes >15 minutes | Heartbeat updates every 60s. Stale check uses heartbeat (2-min threshold). |

---

## 6. Testing Strategy

### Unit Tests
| Component | Test Focus | Priority |
|-----------|-----------|----------|
| Soft-delete push detection | NULL→non-NULL deleted_at = soft-delete, else normal upsert | HIGH |
| Pre-check logic | Same ID → upsert, different ID → reject, no match → insert | HIGH |
| 23505 after clean pre-check | Treated as retryable, not permanent | HIGH |
| Company ID validation | Mismatch → rejected (projects only), null → stamped, match → pass | HIGH |
| Error categorization | 23505 → constraint, 42501 → RLS, 401 → auth, network → retry | HIGH |
| Conflict resolver null timestamps | Null remote + valid local → local wins | MED |
| Conflict resolver snapshot | Stale snapshot detected → uses current record | MED |
| Circuit breaker | Threshold exceeded → paused, below → continues | MED |
| FK per-record blocking | Failed parent A blocks child of A, not child of B | MED |
| Cursor reset tolerance | Below threshold → no reset, above → reset | MED |
| Orphan scanner age filter | <24h → skip, >24h → delete, cap at 50 | MED |

### Integration Tests
| Flow | Verification |
|------|-------------|
| Push soft-deleted project | Remote row has `deleted_at` set, not hard-deleted |
| Pull soft-deleted record | Local row gets `deleted_at` set, filtered from queries |
| Push project with duplicate number | Pre-check catches it, clear error, no crash |
| Photo upload Phase 2 failure | Phase 1 file cleaned up from storage |
| Concurrent edit during conflict resolution | Snapshot detects newer edit, uses current version |
| Admin fetches join requests | RPC returns display_name + email |
| stamp_deleted_by trigger | Client sends wrong deleted_by → server overrides with auth.uid() |

### SQLite Migration Tests
| Scenario | Verification |
|----------|-------------|
| Clean install | UNIQUE index on personnel_types created (if needed) |
| Upgrade with existing data | No errors, existing constraints preserved |

---

## 7. Security

### RLS & Authorization
| Change | Security Impact |
|--------|----------------|
| Soft-delete push (UPDATE not DELETE) | All 16 synced tables have compatible UPDATE RLS policies (verified by security review). No policy changes needed. |
| `stamp_deleted_by()` trigger | Prevents `deleted_by` spoofing. Server enforces `auth.uid()`. |
| Company ID validation | Client-side defense-in-depth on `projects` table. Other tables scoped via FK chain. |
| Pre-check query | Uses existing SELECT RLS. **Not a security boundary** — UNIQUE constraint is the real guard. |
| `get_pending_requests_with_profiles` | SECURITY DEFINER, guarded by `is_approved_admin()` + company match. Minimal PII: display_name + email. |
| `view_own_request` RLS tightening | Deactivated admins can no longer see join requests via direct table query. |
| Orphan auto-delete | Company-scoped storage prefix. Storage RLS restricts DELETE to own company. |
| `assert()` → runtime checks | AdminRepository protected in release builds. |

### Threat Vectors Addressed
| Threat | Mitigation |
|--------|-----------|
| `deleted_by` spoofing | `stamp_deleted_by()` trigger forces `auth.uid()` |
| Cross-company data push | Client-side company_id check + server RLS |
| Deactivated admin sees requests | `view_own_request` RLS uses `is_approved_admin()` |
| TOCTOU on pre-check | 23505 categorized as retryable safety net |
| Orphan scanner deletes active upload | 24h age threshold |

---

## 8. Migration & Cleanup

### Supabase Migrations (2 files)

**`20260313100000_sync_engine_hardening.sql`**:
- `stamp_deleted_by()` function + BEFORE UPDATE triggers on all 16 synced tables
- Tighten `view_own_request` RLS policy to use `is_approved_admin()`
- Backfill `user_profiles.email` from `auth.users.email` where NULL
- Verify `deleted_at`/`deleted_by` columns exist on all 16 synced tables (assertion query)

**`20260313100001_get_pending_requests_with_profiles.sql`**:
- New RPC + REVOKE anon + GRANT authenticated

### SQLite Migration
In `_onUpgrade`: Verify `personnel_types` UNIQUE constraint. Add `last_heartbeat` column to `sync_lock` table. Bump DB version.

### Dead Code
| Item | Action |
|------|--------|
| Hard delete path in `_pushDelete()` | Replace with soft-delete UPDATE detection |
| Generic "Permanent: $message" | Replace with categorized error handler |
| Log-only orphan scanner | Add auto-delete with age/cap guards |

### Backward Compatibility
- Old clients that hard-delete: pull side handles missing records (treat as deleted locally)
- RPC is additive: old clients still work with direct table query (truncated UUID)
- `stamp_deleted_by()` trigger works transparently for all clients

---

## Decisions Log

| Decision | Rationale |
|----------|-----------|
| Reject duplicate project numbers (not merge) | Project number is globally unique within a company. First device to sync wins. |
| Pre-check before push (not onConflict) | User preferred proactive prevention. Pre-check is UX optimization; UNIQUE constraint is the real guard. |
| Local soft-delete (Option A) | App sets `deleted_at` locally (UPDATE trigger). Enables undo. All queries filter `WHERE deleted_at IS NULL`. |
| Keep pull cursor safety margin | Review found removing 5s margin creates data loss from transaction commit skew. Keep existing `gte` + margin. |
| `stamp_deleted_by()` server trigger | Prevents client-side spoofing of deletion attribution. |
| Backfill user_profiles.email | Without it, admin sees null emails for existing users in join requests. |
| Tighten view_own_request RLS | Deactivated admins shouldn't see join requests. New RPC uses `is_approved_admin()` but old path was open. |
| Replace assert() with runtime checks | assert() stripped in release builds. AdminRepository needs real validation. |
| Soft-delete parents don't cascade to children | If you delete a contractor, their equipment should disappear (by RLS design). Not a bug. |
| 24h orphan age threshold | Prevents deleting files from in-progress uploads. |
| 15-minute mutex + heartbeat | Balances stuck-lock recovery and legitimate long syncs. |
| Max 3 integrity resets before diagnostic | Prevents infinite re-pull loops. |
| Circuit breaker threshold configurable | 1000 default may be too low for bulk imports in larger companies. |

---

## Deferred Items

| Item | Reason | Tracked |
|------|--------|---------|
| Empty project list blocks children (Issue 7) | Edge case for first-time setup | LATER |
| Dedup by timestamp equality (Issue 16) | Extremely unlikely in practice | LATER |
| EXIF GPS stripping bare catch (Issue 17) | Low probability failure | LATER |
| HEIC EXIF stripping (Issue 18) | Bundle with Issue 17 | LATER |

---

## Review Findings Addressed

| Finding | Source | Resolution |
|---------|--------|-----------|
| MF-1: Phantom tables | Code review | Corrected to actual table names. 3 already constrained, 2 don't exist, 1 needs verification. |
| MF-2: Soft-delete trigger ambiguity | Code review | Resolved: Option A (local soft-delete, UPDATE trigger). |
| MF-3: Don't remove safety margin | Code review | Section 3H changed to "keep existing." No code change. |
| MF-4: 23505 after clean pre-check | Code review | Treated as retryable, not permanent. |
| MF-5: deleted_by spoofing | Security review | `stamp_deleted_by()` trigger added. |
| MF-6: assert() in release | Security review | Replace with runtime `throw StateError()`. |
| SC-2: company_id scope | Security review | Clarified: only `projects` has company_id. Others scoped via FK chain. |
| SC-3: view_own_request RLS | Security review | Tightened to use `is_approved_admin()`. |
| SC-4: email backfill | Security review | One-time migration from auth.users. |
| SC-5: Pre-check not security boundary | Security review | Documented in spec. UNIQUE constraint is the real guard. |
| H8: fromJson missing fields | Code review | `CompanyJoinRequest.fromJson` updated to parse display_name/email. |
| A2: onConflict vs pre-check | Code review | User chose pre-check only. Dropped adapter onConflict architecture. |
| A3: Keep safety margin | Code review | Accepted. Section 3H removed. |
