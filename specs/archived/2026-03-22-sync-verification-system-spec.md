# Sync Verification System — Spec

**Date**: 2026-03-22
**Status**: Approved
**Supersedes**: `2026-03-19-e2e-sync-verification-spec.md` (partial, never implemented)

## Overview

### Purpose
Three-layer testing system that proves data integrity across all 16 synced tables — every CRUD operation, every sync direction, every conflict scenario, every role boundary. Zero gaps.

### Scope

**Included:**
- Layer 1: Unit tests for critical sync engine risks (SQLite-only)
- Layer 2: Driver-automated E2E for all 16 tables × 5 scenarios (create, update, soft-delete, conflict, fresh-pull) against live Supabase
- Layer 3: Multi-device cross-role testing (Windows admin + Samsung S21+ inspector), orchestrated by debug server
- Debug server expansion: Supabase verification (service role + per-role JWTs), device orchestration, ADB airplane mode control
- Offline/reconnect scenarios via ADB airplane mode
- Cleanup of obsolete test flows, registry references, and agent/skill references

**Excluded:**
- Fixing critical sync risks (C1-C4) — tests expose them, fixes come after
- Performance/load testing (sync with 1000+ records)
- Background sync testing (WorkManager/Timer)
- FCM push-triggered sync testing
- CI/CD integration (local dev machine only)

### Success Criteria
- All 16 tables pass create → push → Supabase verify → pull → local verify
- All 16 tables pass update, soft-delete, conflict, and fresh-pull scenarios
- Multi-device admin/inspector scenarios pass for cross-role visibility
- Offline entry → reconnect → sync completes without data loss
- RLS validation: inspector cannot see admin-only data, admin sees inspector data within company
- All tests repeatable via single command from debug server
- All obsolete test flows and stale references removed

---

## Infrastructure Components

No new database tables or schema changes. Purely test infrastructure.

| Component | Location | Purpose |
|-----------|----------|---------|
| Sync verification module | `tools/debug-server/` | Node.js endpoints querying Supabase (service role + per-role) |
| Device orchestrator | `tools/debug-server/` | Sends commands to both drivers, controls ADB, sequences test phases |
| Test runner | `tools/debug-server/` | Executes scenario files, reports pass/fail |
| Scenario definitions | `tools/debug-server/scenarios/` | JS files defining 85+ test flows |
| Driver sync endpoints | `lib/test_harness/` | `/driver/sync`, `/driver/sync-status`, `/driver/remove-from-device`, `/driver/local-record`, `/driver/create-record` |
| CLI entry point | `tools/debug-server/run-tests.js` | Command-line interface for running tests |

### Data Flow

```
Debug Server (orchestrator, port 3947)
  ├── sends UI commands to → Driver (Windows app, port 3948)
  ├── sends UI commands to → Driver (Samsung app, port 3949 via ADB forward)
  ├── queries Supabase directly (service role key) → ground truth verification
  ├── queries Supabase per-role (admin JWT, inspector JWT) → RLS verification
  ├── toggles ADB airplane mode → offline scenarios
  └── collects results → pass/fail report per table × scenario
```

### Device Setup

```
Debug Server (port 3947)
  ├── Windows driver:  http://localhost:3948
  ├── Samsung driver:  http://localhost:3949 (via adb -s RFCNC0Y975L reverse tcp:3949 tcp:3949)
  └── Samsung ADB:     adb -s RFCNC0Y975L
```

Both apps built with `--dart-define=DEBUG_SERVER=true`.

### Supabase Auth Tokens

| Credential | Source | Purpose |
|-----------|--------|---------|
| Service role key | `.env` (gitignored) | Bypasses RLS for ground truth verification |
| Admin JWT | Runtime auth via debug server | Admin-scoped RLS validation |
| Inspector JWT | Runtime auth via debug server | Inspector-scoped RLS validation |
| Admin email/password | `.env` | Used by debug server to generate JWT |
| Inspector email/password | `.env` | Used by debug server to generate JWT |

### New Driver Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /driver/sync` | Trigger manual sync, return when complete |
| `GET /driver/sync-status` | Return current sync state + pending change_log count |
| `POST /driver/remove-from-device` | Remove active project from device (for fresh-pull S5) |
| `GET /driver/local-record` | Query local SQLite for a specific table + ID, return row data |
| `POST /driver/create-record` | Create a record directly via repository (bypasses UI for setup speed) |

---

## Test Scenario Matrix

### Per-Table Scenarios (80 flows)

Every synced table gets 5 scenarios:

| # | Scenario | What It Proves |
|---|----------|----------------|
| S1 | **Create → Push → Verify** | Data created locally arrives on Supabase with correct fields |
| S2 | **Update → Push → Verify** | Mutations propagate, `updated_at` refreshed server-side |
| S3 | **Soft-Delete → Push → Verify** | `deleted_at`/`deleted_by` set remotely, `stamp_deleted_by` trigger fires |
| S4 | **Conflict (both edit)** | LWW resolves correctly, loser logged in `conflict_log`, winner persists |
| S5 | **Fresh-Pull (Remove → Re-sync)** | Data on Supabase pulls correctly to clean local state |

### Tables (FK dependency order)

| # | Table | S1 | S2 | S3 | S4 | S5 | Notes |
|---|-------|----|----|----|----|-----|-------|
| 1 | projects | ✓ | ✓ | ✓ | ✓ | ✓ | Root table, natural key uniqueness |
| 2 | project_assignments | ✓ | ✓ | ✓ | ✓ | ✓ | Pull-only; S1-S3 test admin RPC path |
| 3 | locations | ✓ | ✓ | ✓ | ✓ | ✓ | FK: project |
| 4 | contractors | ✓ | ✓ | ✓ | ✓ | ✓ | FK: project |
| 5 | equipment | ✓ | ✓ | ✓ | ✓ | ✓ | FK: contractor (deep chain) |
| 6 | bid_items | ✓ | ✓ | ✓ | ✓ | ✓ | FK: project |
| 7 | personnel_types | ✓ | ✓ | ✓ | ✓ | ✓ | FK: project + contractor |
| 8 | daily_entries | ✓ | ✓ | ✓ | ✓ | ✓ | FK: project + location |
| 9 | photos | ✓ | ✓ | ✓ | ✓ | ✓ | Three-phase push, blob verification |
| 10 | entry_equipment | ✓ | ✓ | ✓ | ✓ | ✓ | Junction table, `/driver/create-record` |
| 11 | entry_quantities | ✓ | ✓ | ✓ | ✓ | ✓ | Junction table, FK: entry + bid_item |
| 12 | entry_contractors | ✓ | ✓ | ✓ | ✓ | ✓ | Junction table, FK: entry + contractor |
| 13 | entry_personnel_counts | ✓ | ✓ | ✓ | ✓ | ✓ | Deepest FK chain |
| 14 | inspector_forms | ✓ | ✓ | ✓ | ✓ | ✓ | Has template BLOB |
| 15 | form_responses | ✓ | ✓ | ✓ | ✓ | ✓ | JSON columns (response_data, table_rows) |
| 16 | todo_items | ✓ | ✓ | ✓ | ✓ | ✓ | Simple table |
| 17 | calculation_history | ✓ | ✓ | ✓ | ✓ | ✓ | JSON columns (input_data, result_data) |

### Scenario Execution Pattern

```
1. SETUP    — Create prerequisite parent records (FK deps)
2. ACTION   — Perform CRUD operation via driver (or /driver/create-record for junction tables)
3. SYNC     — POST /driver/sync, wait for completion
4. VERIFY   — Debug server queries Supabase (service role + per-role)
5. TEARDOWN — Soft-delete test data
```

### Scenario Type Details

**S1: Create → Push → Verify**
- Driver creates record via UI (or `/driver/create-record` for junction tables)
- Trigger sync
- Verify: row exists on Supabase with matching fields (service role)
- Verify: row visible to both admin and inspector roles (RLS)
- For photos: verify file exists in Supabase Storage + metadata row matches

**S2: Update → Push → Verify**
- Prerequisite: S1 record exists and is synced
- Driver edits a field via UI
- Trigger sync
- Verify: updated field matches on Supabase
- Verify: `updated_at` is server-assigned (newer than pre-edit value)

**S3: Soft-Delete → Push → Verify**
- Prerequisite: S1 record exists and is synced
- Driver deletes the record via UI
- Trigger sync
- Verify: `deleted_at` set on Supabase, `deleted_by` matches `auth.uid()`
- Verify: record filtered from default queries
- For photos: verify storage file queued for cleanup

**S4: Conflict (both edit)**
- Prerequisite: S1 record synced to both local and Supabase
- Debug server directly updates record on Supabase (simulating another device) with newer `updated_at`
- Driver edits same record locally (older `updated_at`)
- Trigger sync
- Verify: remote wins (LWW), `conflict_log` entry exists
- Then reverse: local edit newer, verify local wins and re-pushes

**S5: Fresh-Pull (Remove → Re-sync)**
- Prerequisite: S1 record exists on Supabase
- Driver calls `/driver/remove-from-device`
- Driver re-enrolls project, triggers sync
- Verify via `/driver/local-record`: pulled record matches Supabase exactly
- For photos: verify file downloaded from Storage

### Table-Specific UI Paths

| Table | UI Path for Create | Special Considerations |
|-------|-------------------|----------------------|
| projects | Project list → Create | Natural key uniqueness (company_id + project_number) |
| project_assignments | Admin panel → Assign user | Pull-only; S1-S3 test admin RPC → Supabase → pull |
| locations | Entry → Add location | FK: project |
| contractors | Project → Contractors tab → Add | FK: project |
| equipment | Contractor detail → Add equipment | FK: contractor (deep chain) |
| bid_items | Project → Bid Items → Add | FK: project |
| personnel_types | Contractor detail → Personnel Types → Add | FK: project + contractor |
| daily_entries | Project → New Entry | FK: project + location |
| photos | Entry → Camera/Gallery | Three-phase push, blob verification |
| entry_equipment | Entry → Equipment section → Add | Junction — `/driver/create-record` |
| entry_quantities | Entry → Quantities → Add | Junction, FK: entry + bid_item |
| entry_contractors | Entry → Contractors section → Add | Junction, FK: entry + contractor |
| entry_personnel_counts | Entry → Personnel section → Add | Junction, deepest FK chain |
| inspector_forms | Toolbox → Forms → Create | Template BLOB |
| form_responses | Form → Fill out → Submit | JSON columns |
| todo_items | Toolbox → Todos → Add | Simple |
| calculation_history | Toolbox → Calculator → Save | JSON columns |

---

## Cross-Cutting Scenarios (Layer 3)

10 multi-device scenarios. Windows (admin) + Samsung S21+ (inspector).

### X1: Admin creates project → Inspector pulls
```
1. Windows (admin): Create project "X1-CrossRole-Project"
2. Windows: Trigger sync → verify on Supabase
3. Samsung (inspector): Trigger sync
4. Samsung: Verify project appears in local DB via /driver/local-record
5. Debug server: Verify both devices have identical data
```

### X2: Inspector creates entry → Admin sees it
```
1. Samsung (inspector): Create daily entry on shared project
2. Samsung: Trigger sync → verify on Supabase
3. Windows (admin): Trigger sync
4. Windows: Verify entry appears locally
5. Debug server: Cross-compare — both have same entry
```

### X3: Both edit same entry simultaneously
```
1. Both devices have entry synced
2. Windows: Edit entry description to "Admin edit"
3. Samsung: Edit same entry description to "Inspector edit"
4. Samsung: Trigger sync first (server-assigned updated_at)
5. Windows: Trigger sync (conflict detected)
6. Debug server: Verify LWW winner correct based on server timestamps
7. Debug server: Verify conflict_log on losing device
8. Both: Sync again → verify convergence
```

### X4: Admin soft-deletes project → Inspector loses children
```
1. Both devices have project with entries, photos, quantities, contractors
2. Windows (admin): Soft-delete the project
3. Windows: Trigger sync → verify deleted_at on Supabase
4. Samsung (inspector): Trigger sync
5. Debug server: Verify project deleted_at set on Samsung
6. Debug server: Check all child tables — document cascade behavior
7. Debug server: Flag as known risk if children NOT cascaded (C3)
```

### X5: Inspector works offline → reconnects → syncs
```
1. Samsung has synced project with data
2. Debug server: adb airplane_mode ON
3. Samsung: Create new entry + photo + quantities
4. Samsung: Verify /driver/sync-status — pending count > 0
5. Debug server: adb airplane_mode OFF
6. Samsung: Trigger sync
7. Debug server: Verify all offline data on Supabase
8. Windows: Trigger sync → verify offline data appears
```

### X6: Inspector creates offline → Admin creates conflicting record
```
1. Debug server: adb airplane_mode ON (Samsung offline)
2. Samsung: Create entry with location "Building A"
3. Windows: Create entry on same project, same date
4. Windows: Trigger sync
5. Debug server: adb airplane_mode OFF
6. Samsung: Trigger sync → conflict
7. Debug server: Verify LWW resolution, conflict_log, final state
```

### X7: Photo taken offline → sync after reconnect
```
1. Debug server: adb airplane_mode ON
2. Samsung: Take photo on entry
3. Verify: photo in local SQLite with file_path, no remote_path
4. Debug server: adb airplane_mode OFF
5. Samsung: Trigger sync
6. Debug server: Verify photo metadata on Supabase
7. Debug server: Verify file in Supabase Storage
8. Samsung: Verify local record has remote_path
```

### X8: RLS — Inspector cannot see admin-only data
```
1. Debug server: Query Supabase as inspector JWT
2. Verify: company_join_requests not accessible
3. Verify: other company's projects not visible
4. Verify: project_assignments only returns inspector's own
```

### X9: RLS — Admin can see inspector's data
```
1. Samsung: Create entry + photo (inspector-owned)
2. Samsung: Trigger sync
3. Debug server: Query as admin JWT — entry and photo visible
4. Debug server: Query as inspector JWT — same visible
5. Debug server: Query as service role — company_id matches
```

### X10: FK ordering under load
```
1. Samsung: Rapidly create project + location + contractor + entry + photo + quantities + equipment
2. Samsung: Trigger sync (all in one batch)
3. Debug server: Verify ALL records on Supabase
4. Debug server: Check change_log — zero 23503 FK errors
5. Debug server: Verify ordering — project.updated_at < entry.updated_at < photo.updated_at
```

### Convergence Check

After every cross-device scenario:
- Query Supabase for all `SYNCTEST-` records (service role)
- Query both devices via `/driver/local-record`
- Diff all three: Supabase vs Windows vs Samsung
- Any divergence = FAIL with detailed diff

---

## Layer 1: Unit Tests for Critical Risks

SQLite-only tests expanding existing 30 test files.

### New Test Files

| File | Risk | What It Tests |
|------|------|---------------|
| `test/features/sync/engine/pull_cursor_safety_test.dart` | C1, C2 | Cursor only advances past successfully processed records. FK-skipped records do NOT advance cursor. |
| `test/features/sync/engine/pull_transaction_test.dart` | C1 | Pull batch atomic — page failure prevents cursor advance. |
| `test/features/sync/engine/cascade_soft_delete_test.dart` | C3 | Soft-deleting project marks all children deleted across 15 child tables via SoftDeleteService. |
| `test/features/sync/engine/trigger_suppression_recovery_test.dart` | C4 | Stuck `sync_control.pulling='1'` reset by next pushAndPull(). Post-recovery edits generate change_log entries. |
| `test/features/sync/engine/conflict_clock_skew_test.dart` | H1 | LWW with timestamps offset by 1s, 5m, 1h. Server-assigned updated_at normalization. |
| `test/features/sync/engine/photo_partial_failure_test.dart` | H2 | Phase 1+2 failure → cleanup. Phase 1+2+3 failure → safe re-push (idempotent). |
| `test/features/sync/engine/tombstone_protection_test.dart` | M1 | Local soft-delete not overridden by remote edit when tombstone in change_log. |
| `test/features/sync/engine/change_log_purge_safety_test.dart` | M2 | Purge rules: >=5 retries + >7 days = purged. <5 retries = kept. Active pending = never purged. |

### Existing Test Enhancements

| File | Enhancement |
|------|-------------|
| `conflict_resolver_test.dart` | Ping-pong circuit breaker: 3+ consecutive local-wins stops re-push |
| `change_tracker_test.dart` | Circuit breaker threshold: >1000 pending triggers auto-purge then trip |
| `cascade_delete_trigger_test.dart` | Soft-delete cascade (currently only hard-delete CASCADE tested) |

**Total: 8 new + 3 enhanced = 11 test files**

---

## Test Data Strategy

- All test data uses `SYNCTEST-{scenario}-{table}-{uuid}` naming
- Each run gets a unique run ID (timestamp-based)
- Teardown soft-deletes all data for the run ID
- `--clean` flag hard-deletes all `SYNCTEST-` data from Supabase before starting
- Tests never touch non-test data

---

## Execution Order & Failure Handling

### Execution Order

```
Layer 1 (unit)  →  must pass  →  Layer 2 (E2E)  →  must pass  →  Layer 3 (multi-device)
```

Within Layer 2: FK dependency order. Within each table: S1 → S2 → S3 → S4 → S5.

### Failure Handling

| Failure Type | Behavior |
|-------------|----------|
| Single scenario fails | Log, continue to next scenario |
| All scenarios for table fail on S1 | Skip S2-S5 for that table |
| Driver connection lost | Retry 3x with 5s backoff, then abort |
| Supabase unreachable | Abort entire run |
| ADB connection lost | Abort Layer 3, Layer 2 can continue |

### Report Format

```
═══════════════════════════════════════════════
  SYNC VERIFICATION REPORT — Run {timestamp}
═══════════════════════════════════════════════

  Layer 1: Unit Tests          11/11  PASS
  Layer 2: E2E (16 tables)     80/80  PASS
  Layer 3: Multi-Device        10/10  PASS

  Convergence Check:           PASS
  RLS Validation:              PASS

  Total: 101/101 (100.0%)
  Duration: {time}
═══════════════════════════════════════════════
```

Saved to `tools/debug-server/reports/sync-verify-{timestamp}.txt`.

### CLI

```bash
node tools/debug-server/run-tests.js --all
node tools/debug-server/run-tests.js --table projects
node tools/debug-server/run-tests.js --scenario conflict
node tools/debug-server/run-tests.js --layer 3
node tools/debug-server/run-tests.js --table photos --step
node tools/debug-server/run-tests.js --clean
```

---

## Security

### Credentials
- Service role key: `.env` only, debug server only, never in app builds
- Admin/Inspector JWTs: generated at runtime, ephemeral
- `tools/` directory excluded from release builds
- `.env` is gitignored

### Test Data on Production Supabase
- `SYNCTEST-` prefix for identification
- `--clean` teardown after runs
- Soft-delete = immediate invisibility, hard-purge by server cron after 30 days

### RLS Validation (X8, X9)
- Inspector JWT must NOT see other companies' data or admin RPCs
- Admin JWT must see all company data
- Cross-company isolation verified

### No New Attack Surface
- Driver/debug gated behind compile-time `--dart-define=DEBUG_SERVER=true`
- No new RLS policies, schema changes, or Supabase functions

---

## Obsolete Test Cleanup

### Flows Removed from Registry

| Flow | Reason |
|------|--------|
| T78: Sync Push — Project Create | Replaced by S1 for projects |
| T79: Sync Push — Entry Create | Replaced by S1 for daily_entries |
| T80: Sync Push — Photo Upload | Replaced by S1 for photos |
| T81: Sync Push — Soft Delete | Replaced by S3 for all tables |
| T82: Sync Push — Edit Mutation | Replaced by S2 for all tables |
| T83: Manual Sync via Settings | Replaced by debug server orchestration |
| T84: Verify Sync Dashboard Counts | Subsumed by convergence check |
| T50: Trigger Manual Sync | Replaced by debug server orchestration |
| M06: Offline Entry then Reconnect Sync | Replaced by X5 + X7 (automated) |

**9 flows removed.**

### Registry Column Cleanup
- Remove `Verify-Sync` column from all CRUD flows (T05-T77)
- CRUD flows test CRUD only; sync verification is now the debug server's job

### Reference Updates Required

| File | What to Update |
|------|---------------|
| `.claude/test-flows/registry.md` | Remove T78-T84, T50, M06. Remove Verify-Sync column. Add "Sync Verification" section pointing to debug server. Update totals. |
| `.claude/autoload/_state.md` | Update test result references to point to new system |
| `.claude/rules/sync/sync-patterns.md` | Update testing section to reference `run-tests.js` |
| `.claude/rules/testing/patrol-testing.md` | Update sync testing section to reference debug server |
| `.claude/docs/` | Grep for T78-T84, M06, "Verify-Sync" — update all references |
| `.claude/agents/` | Grep for old flow IDs — update any agent that references Tier 10 flows |
| `.claude/skills/` | Grep for old flow IDs — update any skill referencing old patterns |
| `.claude/memory/MEMORY.md` | Update test results section |

---

## Implementation Scope

| Component | Files | Effort |
|-----------|-------|--------|
| Layer 1: Unit tests | 8 new + 3 enhanced | Moderate |
| Driver endpoints | 5 new endpoints | Small |
| Debug server: Supabase verifier | New module | Moderate |
| Debug server: Device orchestrator | New module | Moderate |
| Debug server: Test runner | New module | Moderate |
| Layer 2: Scenario files | 80 scenarios (templated) | Large |
| Layer 3: Scenario files | 10 cross-cutting | Moderate |
| CLI entry point | `run-tests.js` | Small |
| Obsolete flow cleanup | Registry + references | Small |

### What Does NOT Get Built
- No fixes for critical risks (C1-C4, H1-H2) — tests expose them
- No new database tables or migrations
- No changes to sync engine or production app behavior
- No CI/CD integration

### Dependencies
```
Driver endpoints → before Layer 2
Debug server verifier → before any Supabase verification
Debug server orchestrator → before Layer 3
Layer 1 pass → before Layer 2
Layer 2 pass → before Layer 3
```

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Supabase verification location | Debug server (not driver) | Neutral observer for multi-device; driver stays UI-focused |
| Supabase auth approach | Service role + per-role JWTs | Ground truth AND RLS validation |
| Fresh device simulation | Remove-from-device feature | Tests real code path, automatable |
| Multi-device orchestration | Fully automated via debug server | Repeatable, both drivers controlled programmatically |
| Offline simulation | ADB airplane mode | Real network conditions, automatable |
| Table coverage | All 16 × 5 scenarios (80 flows) | Data is critical, no shortcuts |
| Alternatives rejected | Option A (two-device manual only) — not repeatable. Option C (mock Supabase) — doesn't test real behavior. |
