# Sync Test Redesign + Hard-Delete Orphan Fix

**Date:** 2026-03-24
**Status:** APPROVED
**Session:** S636

---

## Overview

### Purpose
Two coupled fixes: (1) Redesign the sync verification test system around a shared TestContext to eliminate per-scenario project pollution and duplication across 67 files. (2) Fix the sync engine hard-delete orphan bug that causes the app to appear offline when server records are hard-deleted.

### Scope

**Included:**
- `TestContext` class + shared fixture lifecycle in `scenario-helpers.js`
- `TestRunner` setup/teardown orchestration in `run-tests.js`
- Rewrite all 84 L2 + 10 L3 scenario files to use shared context
- 8 new `make*()` factories for tables missing them
- Sync engine Fix A: `_pushDelete()` treats missing server record as success
- Sync engine Fix B: Orphan purge pass in `IntegrityChecker`
- Sync engine Fix C: `_isTransientError()` hardening
- `--cleanup-only` and `--keep-fixture` CLI flags
- SYNCTEST-* sweep in teardown
- Widget key verification + fixes for S1 UI-navigation scenarios
- RLS policy audit for all 16 synced tables

**Excluded:**
- BLOCKER-28 (SQLite encryption) — separate effort
- BLOCKER-23 (Flutter Keys propagation to Android resource-id) — separate effort

### Success Criteria
- [ ] Single shared project per full L2 run (not 84)
- [ ] Each scenario soft-deletes its own test records via the app's sync flow
- [ ] Teardown hard-deletes any survivors + shared fixture + SYNCTEST-* sweep
- [ ] `--cleanup-only` flag removes all test artifacts from Supabase regardless of sync state
- [ ] Hard-deleting Supabase records no longer crashes the app or triggers infinite retry
- [ ] Orphan purge detects and soft-deletes local records missing from server
- [ ] 0 orphaned SYNCTEST-* records left in Supabase after any run (success or failure)
- [ ] All S1 UI-navigation scenarios have correct widget keys verified and attached
- [ ] RLS policies for all 16 synced tables verified to allow service-role seeding and user-role sync operations

---

## Data Model — TestContext

### TestContext Shape

```js
TestContext {
  // Environment (from .env.test)
  companyId: string,
  adminUserId: string,
  inspectorUserId: string,

  // Shared fixture records (created once, used by all scenarios)
  project:           { id, ...fullRecord },
  projectAssignment: { id, ...fullRecord },
  location:          { id, ...fullRecord },
  contractor:        { id, ...fullRecord },
  equipment:         { id, ...fullRecord },
  bidItem:           { id, ...fullRecord },
  personnelType:     { id, ...fullRecord },
  dailyEntry:        { id, ...fullRecord },
  inspectorForm:     { id, ...fullRecord },

  // Convenience accessors
  projectId, locationId, contractorId, equipmentId,
  bidItemId, personnelTypeId, dailyEntryId, inspectorFormId,
}
```

9 shared records (8 parents + 1 project_assignment). All use `SYNCTEST-FIXTURE-` prefix to distinguish from per-scenario `SYNCTEST-{table}-` records.

### New make*() Factories

| Factory | Required Params | Notes |
|---------|----------------|-------|
| `makeProjectAssignment(projectId, userId)` | project_id, user_id, company_id | Needs admin auth for insert |
| `makeEntryContractor(entryId, contractorId)` | daily_entry_id, contractor_id | Junction table |
| `makeEntryEquipment(entryId, equipmentId)` | daily_entry_id, equipment_id | Junction table |
| `makeEntryPersonnelCount(entryId, contractorId, personnelTypeId)` | daily_entry_id, contractor_id, personnel_type_id | Junction table |
| `makeEntryQuantity(entryId, bidItemId)` | daily_entry_id, bid_item_id | Junction table |
| `makeTodoItem(projectId)` | project_id | Optional: daily_entry_id |
| `makeCalculationHistory(projectId)` | project_id | Optional: daily_entry_id |
| `makePhoto(entryId, projectId)` | daily_entry_id, project_id | Optional: location_id |

### Fixes to Existing Factories

- `makeContractor` / `makeEquipment`: add `deleted_at: null, deleted_by: null`
- `makeDailyEntry`: default `status: 'draft', revision_number: 0`
- `makeInspectorForm`: add optional `project_id` parameter
- All factories: accept `namePrefix` override so scenarios can tag their records distinctly

### Scenario Record Ownership

| Scenario Type | Creates Own Record? | Cleans Up Via |
|---------------|-------------------|---------------|
| S1 (push) | Yes — creates locally, pushes to server | Soft-delete via app → sync |
| S2 (update-push) | Yes — seeds in Supabase, syncs to device | Soft-delete via app → sync |
| S3 (delete-push) | Yes — seeds in Supabase, syncs to device | Soft-delete IS the test |
| S4 (conflict) | Yes — seeds in Supabase for conflict testing | Soft-delete via app → sync |
| S5 (fresh-pull) | Yes — seeds in Supabase, verifies re-pull | Soft-delete via app → sync |

Every scenario creates exactly 1-2 records in its target table. Shared parents are never touched.

### FK Dependency Order (teardown)

```
entry_personnel_counts → entry_equipment → entry_quantities →
entry_contractors → photos → calculation_history → todo_items →
form_responses → daily_entries → equipment → personnel_types →
bid_items → contractors → locations → inspector_forms →
project_assignments → projects
```

---

## Test Runner Lifecycle

### CLI Interface

```
node run-tests.js                                    # Full run (setup → L2 → L3 → teardown)
node run-tests.js --layer L2                         # L2 only (still does setup/teardown)
node run-tests.js --layer L2 --table contractors     # Single table
node run-tests.js --cleanup-only                     # Just teardown + SYNCTEST-* sweep
node run-tests.js --keep-fixture                     # Skip teardown (debugging)
node run-tests.js --clean                            # Existing flag: pre-run SYNCTEST-* sweep only
```

### Run Lifecycle

```
1. Pre-flight
   ├── Load .env.test
   ├── Parse CLI flags
   ├── Device readiness check
   └── Supabase connectivity (get_server_time RPC)

2. SYNCTEST-* sweep (always, before setup)
   └── Query all 16 tables for SYNCTEST-* prefix → hard-DELETE in FK order
       (catches orphans from prior crashed runs)

3. Setup shared fixture
   ├── Create TestContext with 9 records via verifier.insertRecord()
   ├── Insert project_assignment (admin auth)
   ├── Sync to device(s) — verify fixture pulled down
   └── Log fixture IDs for debugging

4. Execute scenarios (sequential, grouped by table)
   ├── Per table: S1, S2, S3, S4 run in order
   ├── S5 runs LAST per table (destructive to device state)
   ├── S1 skip gate: if S1 fails, S2-S5 for that table are skipped
   ├── Each scenario receives { verifier, device, ctx }
   ├── Each scenario creates its own test record, tests it, soft-deletes via app
   ├── If soft-delete sync fails → FAIL the scenario, log reason
   └── Up to 3 retries per scenario (existing behavior)

5. Teardown (unless --keep-fixture)
   ├── Query all 16 tables for scenario records still alive
   ├── Hard-DELETE survivors (these are sync failures — already logged)
   ├── Hard-DELETE shared fixture in reverse FK order
   └── Final SYNCTEST-* sweep (catches anything missed)

6. Report
   └── Write timestamped .txt report to tools/debug-server/reports/
```

### Scenario Contract

Current: `async function run({ verifier, device })`
New: `async function run({ verifier, device, ctx })`

Each scenario:
1. Receives `ctx` (TestContext) — reads `ctx.projectId`, `ctx.dailyEntryId`, etc.
2. Creates its own test record using a `make*()` factory + `verifier.insertRecord()` (or driver for S1)
3. Runs its test logic (push/update/delete/conflict/pull)
4. Soft-deletes its test record via the app's delete flow + sync
5. Verifies deletion reached Supabase
6. If soft-delete fails → throws (scenario marked FAILED), record left for teardown safety net

No more inline project creation. No more `cleanupRecords` arrays. No more `cleanup()` calls in finally blocks.

### L3 Scenarios

L3 receives `{ verifier, adminDevice, inspectorDevice, ctx }`. Same shared fixture, synced to both devices during setup.

---

## Scenario Rewrite Patterns

### Pattern: S1 (Push)

```
1. Create test record locally via /driver/create-record (or UI nav for top-level tables)
2. Trigger sync
3. Verify record exists on Supabase via verifier.queryById()
4. Verify change_log cleared (pendingCount === 0)
5. Soft-delete via /driver/delete-record → trigger sync → verify deleted on Supabase
```

### Pattern: S2 (Update-Push)

```
1. Seed test record in Supabase via verifier.insertRecord(table, make*(ctx.parentId))
2. Sync to device → verify record pulled down
3. Update a field via /driver/update-record
4. Trigger sync → verify Supabase has updated value
5. Soft-delete via app → verify cleanup
```

### Pattern: S3 (Delete-Push)

```
1. Seed test record in Supabase
2. Sync to device → verify present
3. Delete via /driver/delete-record (app soft-delete)
4. Trigger sync
5. Verify deleted_at is set on Supabase ← THIS IS THE TEST
```

No teardown needed — the test itself IS the cleanup.

### Pattern: S4 (Conflict)

```
1. Seed test record in Supabase → sync to device
2. Phase 1 (remote wins): update locally, update Supabase with NEWER timestamp
   → sync → verify remote value won
3. Phase 2 (local wins): update locally, update Supabase with OLDER timestamp
   → sync → verify local value won
4. Soft-delete via app → verify cleanup
```

New helper: `runConflictPhase(device, verifier, { table, id, field, localValue, remoteValue, remoteWins })` — extracts the duplicated LWW two-phase logic.

### Pattern: S5 (Fresh-Pull) — runs last per table

```
1. Seed test record in Supabase → sync to device → verify present
2. /driver/remove-from-device (project_id scoped) — purges all project data
3. Re-sync → verify test record AND shared fixture pulled back
4. Soft-delete test record via app → verify cleanup
```

### Common Helpers

| Helper | Replaces | Used By |
|--------|----------|---------|
| `seedAndSync(verifier, device, table, record)` | Inline insertRecord + triggerSync + waitFor | S2, S3, S4, S5 |
| `softDeleteAndVerify(verifier, device, table, id)` | Inline delete-record + triggerSync + verify deleted_at | All except S3 |
| `runConflictPhase(...)` | Duplicated 2-phase LWW block | All S4 scenarios |
| `verifyPulled(device, table, id)` | Inline driver/query + assertion | S1, S5 |
| `waitForSyncClean(device)` | Inline waitFor pendingCount === 0 | S1 |

---

## Sync Engine Hard-Delete Fix

### Fix A — `_pushDelete()` treats missing record as success

**Location:** `sync_engine.dart:600-605`

**Current:** Throws `StateError('Soft-delete push failed: ... remote record not found (0 rows affected)')` when `response.isEmpty`.

**New:** Log via `Logger.sync()`, mark `change_log` entry as processed, return normally. The goal of a soft-delete push is "record should be deleted on server" — if it's already gone, that goal is achieved.

### Fix B — Orphan purge in IntegrityChecker

**Location:** `integrity_checker.dart` — new method `purgeOrphans()`

**Trigger:** Runs during the existing `IntegrityChecker.run()` cycle (periodic, not every sync).

**Logic:**
1. For each table in FK order (parents first → children):
   - Query local SQLite for all record IDs where `deleted_at IS NULL`
   - Filter to records under currently synced projects only
   - Skip any record that has an unprocessed `change_log` entry
   - Batch-query Supabase: `SELECT id FROM table WHERE id IN (batch)` (pages of 100)
   - Diff: `local_ids - server_ids = orphan_ids`
2. For each orphan:
   - Set `pulling = 1` (suppress SQLite triggers)
   - `UPDATE SET deleted_at = now(), deleted_by = 'system_orphan_purge'`
   - Set `pulling = 0`
   - Log via `Logger.sync('Orphan purged: $table/$id — missing from server')`
3. Return count of purged records for the integrity report

Parents processed first so children cascade in single pass.

### Fix C — `_isTransientError()` hardening

**Location:** `sync_orchestrator.dart:413-462`

1. Add to `nonTransientPatterns`: `'remote record not found'`, `'0 rows affected'`, `'Soft-delete push failed'`
2. Flip default branch from `return true` to `return false` + `Logger.sync('WARNING: Unknown error type in _isTransientError, defaulting to non-transient: ...')`
3. Non-transient = fail immediately, no retry loop, no 60s background timer

**Rationale:** Current `return true` default means ANY novel error triggers infinite retries — root cause of the "offline" appearance. Transient errors (network, DNS, rate limits) are already explicitly matched.

---

## Security

### RLS Audit

All 16 synced tables need verification for:
- User-role INSERT/UPDATE for own company's records on assigned projects
- User-role SELECT scoped to assigned projects
- Admin INSERT on `project_assignments`
- Service-role (verifier) bypasses RLS by design — no audit needed

No new RLS policies expected. If a test fails due to RLS, that's a real policy gap affecting production users.

### Hard-DELETE Security

- Only runs in test context (debug server, not production app)
- Service-role key in `.env.test` (gitignored)
- Scoped to `SYNCTEST-*` prefixed records only
- Production app never hard-deletes

### Sync Fix Security

- Fix A: No security impact — push already authenticated, just not throwing on no-op
- Fix B: Local-only (SQLite UPDATEs under trigger suppression). Supabase queries are SELECT-only.
- Fix C: Reduces retry surface — more conservative, not less secure

---

## Widget Keys

S1 scenarios for 4 tables use UI navigation and need verified widget keys:

| Table | S1 Flow | Keys Required |
|-------|---------|--------------|
| projects | Create project via UI | Project creation form keys |
| daily_entries | Create entry via UI | Entry creation form keys |
| todo_items | Create todo via UI | Todo creation form keys |
| calculation_history | Create calculation via UI | Calculator flow keys |

Plan must: verify keys exist in `lib/shared/testing_keys/*.dart`, verify keys are attached to widgets in presentation layer, add missing keys.

---

## Edge Cases

### Test System

| Scenario | What Happens | Recovery |
|----------|-------------|----------|
| Setup fails | Abort run, no teardown needed | Fix seeding issue, re-run |
| Scenario fails mid-test | FAILED, record left alive | Teardown hard-DELETEs survivors |
| Soft-delete sync fails to propagate | FAILED (Supabase still has record) | Teardown hard-DELETEs from Supabase |
| S5 re-pull fails to restore fixture | S5 FAILED, subsequent tables re-sync fixture | Teardown still runs |
| Teardown fails (Supabase unreachable) | Orphans left | Next run's pre-flight sweep catches them |
| Run killed (Ctrl+C, crash) | Fixture + records left | `--cleanup-only` or next run's sweep |
| Device disconnected | Driver timeout → FAIL | Teardown still cleans Supabase |

### Sync Engine

| Scenario | What Happens | Resolution |
|----------|-------------|------------|
| User deletes locally while orphan purge queued | change_log entry → purge skips → Fix A handles | No conflict |
| Admin hard-deletes project from Supabase | Integrity check purges locally → children cascade | App recovers without Clear Data |
| 500+ orphans found | Batched pages of 100, under sync mutex | Longer integrity check, no UI block |
| Novel transient error not in pattern list | Non-transient default → fails once | Visible in WARNING log, add pattern when discovered |

---

## Decisions Log

| # | Decision | Rationale | Alternatives Rejected |
|---|----------|-----------|----------------------|
| 1 | Fix A + C + lightweight Fix B | Covers real-world admin hard-delete scenario | Fix A+C only (leaves orphans silent); Full A+B+C with resurrection handling (overcomplex) |
| 2 | Runner manages fixture, `--cleanup-only` escape hatch | Simple common path, escape hatch for failures | Skill-managed (too much coordination); Runner-only (no escape hatch) |
| 3 | Children-first hard-DELETE + SYNCTEST-* sweep | Catches prior crashed runs, zero orphan guarantee | Project-only with FK CASCADE (depends on Supabase config); Children-first only (misses prior runs) |
| 4 | Scenarios soft-delete own records, hard-DELETE is safety net | Tests the real sync delete flow; failure = real bug | Hard-DELETE everything (doesn't test sync); Leave for teardown (doesn't test per-scenario) |
| 5 | S5 runs last per table, same fixture | S5 tests re-pull which should restore fixture | Separate mini-fixture (defeats shared fixture purpose) |
| 6 | Flipped `_isTransientError` default to non-transient | Infinite retry on unknown errors is worse than one-time failure | Keep `return true` (root cause of offline bug) |
| 7 | Widget keys + RLS audit in scope | S1 scenarios need keys to work; RLS gaps are production bugs | Out of scope (scenarios would fail anyway) |
