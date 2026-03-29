# Sync Verification: Claude-Driven Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Replace Node.js integrity-runner with Claude-driven sync verification flows (S01-S10), updating all test infrastructure references.
**Spec:** `.claude/specs/2026-03-25-sync-verification-claude-driven-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-25-sync-verification-claude-driven/`

**Architecture:** Delete ~105 old JS test scenario files and their runners. Strip `run-tests.js` to cleanup-only mode. Update skill.md and registry.md to reference the new S01-S10 Claude-driven flows. Create a comprehensive sync-verification-guide.md that Claude reads when executing `/test sync`.

**Tech Stack:** Node.js (cleanup script), Markdown (test infrastructure docs), curl + Supabase REST API (verification)

**Blast Radius:** 3 modified, 1 created, ~105 deleted, 0 Dart tests, 0 dependent files

---

## Phase 1: Delete Old JS Infrastructure

### Sub-phase 1.1: Delete Deprecated Scenario Directories

**Files:**
- Delete: `tools/debug-server/scenarios/deprecated/` (entire directory — 84 L2 files + 10 L3 files)

**Agent**: general-purpose

#### Step 1.1.1: Remove deprecated directory tree
```bash
rm -rf tools/debug-server/scenarios/deprecated/
```

### Sub-phase 1.2: Delete Integrity Scenario Files

**Files:**
- Delete: `tools/debug-server/scenarios/integrity/F1-project-setup.js`
- Delete: `tools/debug-server/scenarios/integrity/F2-daily-entry.js`
- Delete: `tools/debug-server/scenarios/integrity/F3-photos.js`
- Delete: `tools/debug-server/scenarios/integrity/F4-forms.js`
- Delete: `tools/debug-server/scenarios/integrity/F5-todos.js`
- Delete: `tools/debug-server/scenarios/integrity/F6-calculator.js`
- Delete: `tools/debug-server/scenarios/integrity/U1-update-all.js`
- Delete: `tools/debug-server/scenarios/integrity/P1-pdf-export.js`
- Delete: `tools/debug-server/scenarios/integrity/D1-delete-cascade.js`
- Delete: `tools/debug-server/scenarios/integrity/D2-unassignment.js`

**Agent**: general-purpose

#### Step 1.2.1: Remove integrity scenarios directory
```bash
rm -rf tools/debug-server/scenarios/integrity/
```

### Sub-phase 1.3: Delete Runner and Helper Modules

**Files:**
- Delete: `tools/debug-server/integrity-runner.js`
- Delete: `tools/debug-server/test-runner.js`
- Delete: `tools/debug-server/device-orchestrator.js`
- Delete: `tools/debug-server/scenario-helpers.js`

**Agent**: general-purpose

#### Step 1.3.1: Remove the four JS modules
```bash
rm -f tools/debug-server/integrity-runner.js
rm -f tools/debug-server/test-runner.js
rm -f tools/debug-server/device-orchestrator.js
rm -f tools/debug-server/scenario-helpers.js
```

---

## Phase 2: Strip run-tests.js to Cleanup-Only Mode

### Sub-phase 2.1: Rewrite run-tests.js

**Files:**
- Modify: `tools/debug-server/run-tests.js`

**Agent**: general-purpose

#### Step 2.1.1: Replace run-tests.js content

Replace the entire file with the following (~80 lines). Preserves:
- Header comments (updated for cleanup-only usage)
- RLS audit comment block (lines 12-59 verbatim — do NOT modify)
- `.env.test` IIFE loader (lines 62-76 verbatim)
- `--cleanup-only` mode
- `--clean` flag
- env validation

Removes:
- `TestRunner` require (line 78)
- `requireArgValue` function (lines 80-93)
- Full `parseArgs` function (lines 95-190) — replace with minimal version
- `--suite=integrity` block (lines 228-233)
- `TestRunner` instantiation block (lines 235-238)
- All flags except `--clean`, `--cleanup-only`, `--help`

New content for the file:

```javascript
#!/usr/bin/env node
// WHY: CLI utility for cleaning up sync verification test data from Supabase
//
// Usage:
//   node tools/debug-server/run-tests.js --cleanup-only   # Sweep SYNCTEST-*/VRF-* records and exit
//   node tools/debug-server/run-tests.js --clean           # Same as --cleanup-only
//
// Sync verification flows (S01-S10) are now Claude-driven.
// See: .claude/test-flows/sync-verification-guide.md

// RLS Audit 2026-03-24: All 17 synced tables verified against supabase/migrations/
//
// TABLES AND RLS STATUS:
//
//   Table                   | RLS Enabled | SELECT | INSERT | UPDATE | DELETE | Notes
//   ------------------------|-------------|--------|--------|--------|--------|------
//   projects                | YES (0317)  | YES    | YES    | YES    | YES    | INSERT/UPDATE/DELETE tightened to is_admin_or_engineer() in 0319200000; soft-delete guard on UPDATE
//   project_assignments     | YES (0319)  | YES    | YES    | YES*   | YES    | UPDATE policy explicitly USING(false) — immutable by design
//   locations               | YES (0317)  | YES    | YES    | YES    | YES    | project_id-scoped; is_viewer() now returns FALSE (viewer role removed 0319200000)
//   contractors             | YES (0317)  | YES    | YES    | YES    | YES    | project_id-scoped
//   equipment               | YES (0317)  | YES    | YES    | YES    | YES    | Two-hop: contractor_id -> contractors -> projects
//   bid_items               | YES (0317)  | YES    | YES    | YES    | YES    | project_id-scoped
//   personnel_types         | YES (0222)  | YES    | YES    | YES    | YES    | WITH CHECK added on UPDATE in 0317000001
//   daily_entries           | YES (0317)  | YES    | YES    | YES    | YES    | project_id-scoped
//   photos                  | YES (0317)  | YES    | YES    | YES    | YES    | project_id-scoped (storage bucket has separate policies)
//   entry_equipment         | YES (0222)  | YES    | YES    | YES    | YES    | Two-hop via entry_id; WITH CHECK added on UPDATE in 0317000001
//   entry_quantities        | YES (0317)  | YES    | YES    | YES    | YES    | Two-hop via entry_id; UPDATE policy lacks explicit WITH CHECK (uses implicit USING)
//   entry_contractors       | YES (0222)  | YES    | YES    | YES    | YES    | Two-hop via entry_id; WITH CHECK added on UPDATE in 0317000001
//   entry_personnel_counts  | YES (0222)  | YES    | YES    | YES    | YES    | Two-hop via entry_id; WITH CHECK added on UPDATE in 0317000001
//   inspector_forms         | YES (0126)  | YES    | YES    | YES    | YES    | project_id-scoped; company-scoped policies added in 0222100000
//   form_responses          | YES (0126)  | YES    | YES    | YES    | YES    | project_id-scoped; company-scoped policies added in 0222100000
//   todo_items              | YES (0126)  | YES    | YES    | YES    | YES    | project_id-scoped; company-scoped policies added in 0222100000
//   calculation_history     | YES (0126)  | YES    | YES    | YES    | YES    | project_id-scoped; company-scoped policies added in 0222100000
//
// FINDINGS (items for user review — NOT auto-fixed):
//
//   FINDING-1 (LOW): entry_quantities UPDATE policy (multi_tenant_foundation.sql:543)
//     Missing explicit WITH CHECK clause. PostgreSQL defaults WITH CHECK to USING for
//     UPDATE policies, so this is functionally correct, but 5 sibling tables received
//     explicit WITH CHECK in migration 20260317000001. entry_quantities was not included.
//     Recommend: add WITH CHECK to entry_quantities UPDATE policy for audit consistency.
//
//   FINDING-2 (INFO): is_viewer() now returns FALSE unconditionally (tighten_project_rls.sql:9)
//     The viewer role was removed in 20260317100000. is_viewer() was replaced with
//     SELECT FALSE rather than being dropped (70+ policy clauses reference it).
//     Consequence: all AND NOT is_viewer() guards are now AND TRUE — the actual gate
//     for write operations is now is_admin_or_engineer() on projects, and no explicit
//     role gate on non-project tables (any approved company member can write).
//     This is the intended design per spec, but worth noting in a future cleanup pass
//     to remove the deprecated function references.
//
//   FINDING-3 (INFO): project_assignments UPDATE policy uses USING(false)
//     This is intentional (assignments are insert-or-delete only, never updated).
//     No action needed.
//
// All policies scope to get_my_company_id() which enforces status = 'approved' (security-critical).
// Storage bucket policies verified separately in 20260305000000_schema_alignment_and_security.sql.

// SEC-001: Load from .env.test (NOT root .env which gets compiled into APK via --dart-define-from-file)
// Zero-dep env loader — no dotenv package required
(function loadEnvTest() {
  const fs = require('fs');
  const path = require('path');
  const envPath = path.join(__dirname, '.env.test');
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 1) continue;
    const key = trimmed.slice(0, eq).trim();
    const val = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '');
    if (!(key in process.env)) process.env[key] = val;
  }
}());

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case '--clean':
        args.clean = true;
        break;
      case '--cleanup-only':
        args.cleanupOnly = true;
        break;
      case '--help':
        console.log(`
Sync Verification Cleanup Utility

Usage: node run-tests.js [options]

Options:
  --cleanup-only       Sweep SYNCTEST-*/VRF-* records from Supabase and exit
  --clean              Same as --cleanup-only
  --help               Show this help

Sync verification flows (S01-S10) are now Claude-driven.
See: .claude/test-flows/sync-verification-guide.md
        `);
        process.exit(0);
      default:
        console.error('Unknown flag:', argv[i]);
        process.exit(1);
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);

  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    console.error('Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in tools/debug-server/.env.test');
    process.exit(1);
  }

  if (args.cleanupOnly || args.clean) {
    console.log('=== Cleanup mode ===');
    const SupabaseVerifier = require('./supabase-verifier');
    const verifier = new SupabaseVerifier(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
    const synctestSwept = await verifier.sweepSynctestRecords();
    const vrfSwept = await verifier.sweepVrfRecordsByPrefix();
    console.log(`Swept ${synctestSwept + vrfSwept} SYNCTEST/VRF records`);
    process.exit(0);
  }

  console.log('No action specified. Use --cleanup-only or --help.');
  process.exit(0);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
```

**Verification:** Run `node tools/debug-server/run-tests.js --help` and confirm it prints the new help text without errors.

---

## Phase 3: Update Skill and Registry References

### Sub-phase 3.1: Update skill.md Sync Section

**Files:**
- Modify: `.claude/skills/test/skill.md`

**Agent**: general-purpose

#### Step 3.1.1: Update tier alias map entry

Replace line 68:
```
sync         → node tools/debug-server/run-tests.js (L2/L3 scenarios)
```
With:
```
sync         → S01-S10 (Claude-driven dual-device verification)
```

#### Step 3.1.2: Update usage examples

Add these lines after the existing `/test sync` line (line 44) — replace that single line with:
```
/test sync                         # S01-S10 (Claude-driven dual-device)
/test S01                          # Single sync flow
/test S01-S03                      # Range of sync flows
/test sync --resume                # Resume from checkpoint
```

#### Step 3.1.3: Replace the Sync line in Flow Dependencies

Replace line 287:
```
**Sync** — Sync Verification via `node tools/debug-server/run-tests.js` (L2/L3 scenarios, not driver flows)
```
With:
```
**Sync (S01-S10)** — Claude-driven dual-device sync verification (admin:4948, inspector:4949)
  S01 (Project Setup) → S02 (Daily Entry) → S03 (Photos) → S04 (Forms) → S05 (Todos) → S06 (Calculator) → S07 (Update All) → S08 (PDF Export) → S09 (Delete Cascade) → S10 (Unassignment + Cleanup)
```

#### Step 3.1.4: Add new section — Sync Verification (Dual-Device)

Insert the following section after the "Flow Dependencies" section (after line 289), before the "Teardown" section:

```markdown
## Sync Verification (Dual-Device) — S01-S10

Claude drives two devices via HTTP driver endpoints and verifies data in Supabase via REST API.

**Reference guide:** `.claude/test-flows/sync-verification-guide.md`

### Setup
- Admin device: port 4948 (Android or Windows)
- Inspector device: port 4949 (second device)
- Supabase credentials: `tools/debug-server/.env.test` (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
- Test credentials: `.claude/test-credentials.secret`

### Driver Endpoints Used
All standard endpoints (tap, text, wait, scroll, etc.) plus:
- `POST /driver/sync` — trigger sync on device
- `GET /driver/local-record?table=X&id=Y` — verify record exists locally on device
- `POST /driver/remove-from-device` — remove project from device locally
- `POST /driver/inject-photo-direct` — inject photo with entry/project association

### Cross-Device Sync Protocol (4-Step)
After every data mutation:
1. **Admin sync**: `curl -s -X POST http://127.0.0.1:4948/driver/sync`
2. **Supabase verify**: curl REST API to confirm data arrived
3. **Inspector sync** (2 rounds): `curl -s -X POST http://127.0.0.1:4949/driver/sync` x2
4. **Inspector verify**: `curl -s "http://127.0.0.1:4949/driver/local-record?table=X&id=Y"`

### Supabase Verification Pattern
```bash
curl -s "${SUPABASE_URL}/rest/v1/<table>?<filters>" \
  -H "apikey: ${KEY}" \
  -H "Authorization: Bearer ${KEY}" \
  -H "Accept: application/json"
```

### Per-Run Unique Data Tag
Every run generates a 5-char alphanumeric tag. All test data uses prefix `VRF-` with this tag embedded in names to avoid collisions.

### Compaction Pauses
After S03, S06, and S09 — checkpoint written, user prompted to continue.

### Post-Run Sweep
After S10, query all 17 synced tables for `VRF-*` records. Any remaining = FAIL.
```

#### Step 3.1.5: Add sync flows to Flow Dependencies section

Add `S01-S10` to the dependency chain at the end of the Flow Dependencies section.

### Sub-phase 3.2: Update registry.md

**Files:**
- Modify: `.claude/test-flows/registry.md`

**Agent**: general-purpose

#### Step 3.2.1: Replace Sync Verification System blockquote

Replace lines 156-166 (the entire "## Sync Verification System" section including the blockquote) with:

```markdown
## Sync Verification — Claude-Driven (S01-S10)

> Dual-device sync verification. Claude drives admin (port 4948) and inspector (port 4949), verifies data via Supabase REST API.
> Reference: `.claude/test-flows/sync-verification-guide.md`

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Status | Last Run | Notes |
|----|------|----------|--------------|-------------|--------|----------|-------|
| S01 | Project Setup | projects, project_assignments, locations, contractors, equipment, bid_items, personnel_types | Admin: create project + sub-entities + assignment → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Creates 2 projects (main + unassign test); captures all entity IDs |
| S02 | Daily Entry | daily_entries, entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities | Admin: create full entry → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Depends: S01 |
| S03 | Photos | photos | Admin: inject-photo-direct → sync → Inspector: sync x2 → verify locally | sync,photo | UNTESTED | - | Depends: S02; COMPACTION PAUSE after |
| S04 | Forms | inspector_forms, form_responses | Admin: create 0582B response → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Depends: S02 |
| S05 | Todos | todo_items | Admin: create todo → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Depends: S01 |
| S06 | Calculator | calculation_history | Admin: HMA calculation → save → sync → Inspector: sync x2 → verify locally | sync,db | UNTESTED | - | Depends: S01; COMPACTION PAUSE after |
| S07 | Update All | All updatable tables | Admin: update project, location, contractor, equipment, bid_item, personnel_type, entry fields, photo, form, todo, calculator → sync → Inspector: verify | sync,db | UNTESTED | - | Depends: S01-S06 |
| S08 | PDF Export | N/A (output artifact) | Admin: export IDR + 0582B PDFs → ADB pull → pdftk verify fields | pdf | UNTESTED | - | Depends: S07; ADB timeout → FAIL S08, continue to S09 |
| S09 | Delete Cascade | All child tables of project 1 | Admin: two-step delete → sync → Supabase: verify 14 child tables soft-deleted → Inspector: deletion banner → verify gone | sync,db | UNTESTED | - | Depends: S07; COMPACTION PAUSE after |
| S10 | Unassignment + Cleanup | project_assignments, projects | Admin: unassign inspector from project 2 → sync → Inspector: verify project 2 removed → Admin: delete project 2 → post-run VRF sweep | sync,db | UNTESTED | - | Depends: S01 |
```

#### Step 3.2.2: Update Flow Count Summary

Replace the Sync row in the Flow Count Summary table (line 229):
```
| Sync | — | — | Sync verification via `tools/debug-server/run-tests.js` (L2/L3 scenarios) |
```
With:
```
| Sync | S01-S10 | 10 | Sync Verification (Claude-driven, dual-device) |
```

#### Step 3.2.3: Update total count

Replace the total row (line 233):
```
| **Total** | | **95** | **83 automated + 12 manual + sync verification system** |
```
With:
```
| **Total** | | **105** | **83 automated + 12 manual + 10 sync verification (Claude-driven)** |
```

#### Step 3.2.4: Add S01-S10 to Dependency Chain

Add the following after the inspector session block (after line 275) in the Dependency Chain section:

```
S01 (Project Setup) — dual-device session (admin:4948, inspector:4949)
 ├── S02 (Daily Entry) → S03 (Photos) [COMPACTION]
 ├── S04 (Forms)
 ├── S05 (Todos)
 ├── S06 (Calculator) [COMPACTION]
 ├── S07 (Update All) → S08 (PDF Export) → S09 (Delete Cascade) [COMPACTION]
 └── S10 (Unassignment + Cleanup)
```

---

## Phase 4: Create Sync Verification Guide

### Sub-phase 4.1: Write sync-verification-guide.md

**Files:**
- Create: `.claude/test-flows/sync-verification-guide.md`

**Agent**: general-purpose

#### Step 4.1.1: Create the comprehensive guide

Write the full file with these sections. This is the primary reference Claude reads when executing `/test sync`. It must be exhaustive.

```markdown
# Sync Verification Guide (S01-S10)

> Claude-driven dual-device sync verification. This guide is the primary reference
> for executing `/test sync`. Read it fully before starting a sync verification run.

## Environment Setup

### Devices
- **Admin device** (port 4948): Primary device — creates all data
- **Inspector device** (port 4949): Secondary device — pulls and verifies synced data

Both devices must be running the app with `main_driver.dart` entrypoint.

### Credentials
Read from `.claude/test-credentials.secret`:
- Admin account: logged in on port 4948
- Inspector account: logged in on port 4949

### Supabase Access
Load from `tools/debug-server/.env.test`:
- `SUPABASE_URL` — project URL
- `SUPABASE_SERVICE_ROLE_KEY` — service role key (bypasses RLS for verification)

```bash
# Load env vars for the session
eval $(python3 -c "
import os
for line in open('tools/debug-server/.env.test'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        v = v.strip().strip('\"').strip(\"'\")
        print(f'export {k.strip()}=\"{v}\"')
")
```

### Per-Run Unique Tag
Generate a 5-char alphanumeric tag at the start of each run:
```bash
RUN_TAG=$(python3 -c "import random,string; print(''.join(random.choices(string.ascii_lowercase + string.digits, k=5)))")
```
All test data uses names prefixed with `VRF-` and embeds this tag to avoid collisions with prior runs.

## Pre-Run Cleanup

Before starting, sweep any leftover VRF-* data from prior runs:

1. Query Supabase for projects with `VRF-` prefix:
```bash
curl -s "${SUPABASE_URL}/rest/v1/projects?name=like.VRF-*&select=id,name" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
```

2. If any found, remove from both devices:
```bash
curl -s -X POST http://127.0.0.1:4948/driver/remove-from-device -d '{"project_id":"<id>"}'
curl -s -X POST http://127.0.0.1:4949/driver/remove-from-device -d '{"project_id":"<id>"}'
```

3. Hard-delete from Supabase in FK order (see FK Teardown Order below).

4. Alternatively, use the cleanup utility:
```bash
node tools/debug-server/run-tests.js --cleanup-only
```

## Supabase Query Patterns

### Read records
```bash
curl -s "${SUPABASE_URL}/rest/v1/<table>?<filters>&select=<columns>" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Accept: application/json"
```

### Common filters
- By ID: `?id=eq.<uuid>`
- By project: `?project_id=eq.<uuid>`
- By name prefix: `?name=like.VRF-*`
- Not deleted: `?is_deleted=eq.false`
- Include deleted: `?is_deleted=in.(true,false)` or omit filter (service role bypasses RLS)

### Hard-delete (cleanup only)
```bash
curl -s -X DELETE "${SUPABASE_URL}/rest/v1/<table>?id=eq.<uuid>" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
```

## Cross-Device Sync Protocol

Use this 4-step pattern after every data mutation:

### Step 1: Admin Sync
```bash
curl -s -X POST http://127.0.0.1:4948/driver/sync
```
Wait for response (sync complete on admin).

### Step 2: Supabase Verify
Query Supabase REST API to confirm data arrived in the cloud.

### Step 3: Inspector Sync (2 rounds)
```bash
curl -s -X POST http://127.0.0.1:4949/driver/sync
sleep 2
curl -s -X POST http://127.0.0.1:4949/driver/sync
```
Two rounds ensure any FK-dependent records that failed on first pull (missing parent) succeed on second.

### Step 4: Inspector Local Verify
```bash
curl -s "http://127.0.0.1:4949/driver/local-record?table=<table>&id=<uuid>"
```
Confirm the record exists locally on the inspector device.

## Log Scanning

After every operation, check for errors:
```bash
START_TIME="<iso-timestamp-before-operation>"
curl -s "http://127.0.0.1:3947/logs?since=${START_TIME}&level=error"
```

Also check sync-specific logs after sync:
```bash
curl -s "http://127.0.0.1:3947/logs?since=${START_TIME}&category=sync"
```

Any error-level log entries = investigate before proceeding.

## FK Teardown Order

When hard-deleting test data from Supabase, delete in this order to avoid FK violations:

1. `entry_personnel_counts`
2. `entry_equipment`
3. `entry_quantities`
4. `entry_contractors`
5. `photos`
6. `calculation_history`
7. `todo_items`
8. `form_responses`
9. `daily_entries`
10. `equipment`
11. `personnel_types`
12. `bid_items`
13. `contractors`
14. `locations`
15. `inspector_forms`
16. `project_assignments`
17. `projects`

## Checkpoint Schema

Write `.claude/test_results/<run>/checkpoint.json` after every flow:

```json
{
  "run_id": "2026-03-25_14-30",
  "suite": "sync",
  "platform": "dual (android:4948 + windows:4949)",
  "results_dir": ".claude/test_results/2026-03-25_14-30",
  "run_tag": "k1a2b",
  "completed": { "S01": "PASS", "S02": "PASS" },
  "next_flow": "S03",
  "ctx": {
    "project_id": "uuid",
    "project2Id": "uuid",
    "locationIds": ["uuid"],
    "contractorIds": ["uuid"],
    "equipmentIds": ["uuid"],
    "bidItemIds": ["uuid"],
    "personnelTypeIds": ["uuid"],
    "entryId": "uuid",
    "entryContractorIds": ["uuid"],
    "entryEquipmentIds": ["uuid"],
    "entryPersonnelCountIds": ["uuid"],
    "entryQuantityIds": ["uuid"],
    "photoIds": ["uuid"],
    "formResponseIds": ["uuid"],
    "todoIds": ["uuid"],
    "calculationIds": ["uuid"],
    "assignmentId": "uuid"
  },
  "bugs": [],
  "observations": []
}
```

The `ctx` object carries all entity IDs created during the run. This enables:
- Resume from any checkpoint (IDs survive context compaction)
- Cleanup of specific records on failure
- Cross-flow references (e.g., S02 uses `ctx.projectId` from S01)

## Compaction Pauses

After S03, S06, and S09, output:
```
**Checkpoint written. Say 'continue' to proceed.**
```

On resume:
1. Find latest run dir in `.claude/test_results/`
2. Read `checkpoint.json`
3. Load `ctx` to restore all entity IDs
4. Continue from `next_flow`

---

## Flow Protocols

### S01: Project Setup

**Tables:** projects, project_assignments, locations, contractors, equipment, bid_items, personnel_types

**Admin (4948):**

1. Navigate to project creation:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"projects_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_create_button"}'
   sleep 1
   ```

2. Fill project fields:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"project_name_field","text":"VRF-Oakridge '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"project_number_field","text":"VRF-'"${RUN_TAG}"'-001"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"project_client_field","text":"VRF-City of Oakridge '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_save_button"}'
   sleep 2
   ```

3. Sync admin and capture project ID from Supabase:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/sync
   # Query Supabase for the project
   curl -s "${SUPABASE_URL}/rest/v1/projects?name=like.VRF-Oakridge%20${RUN_TAG}*&select=id,name" \
     -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
   # Capture projectId from response
   ```

4. Edit project — add 2 locations:
   ```bash
   # Navigate to project edit → locations tab
   # NOTE: project_edit_menu_item requires projectId — use project_edit_menu_item_<projectId>
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_edit_menu_item_<projectId>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_locations_tab"}'
   sleep 1
   # Location 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_location_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"location_name_field","text":"VRF-Station 12+50 '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"location_dialog_add"}'
   sleep 1
   # Location 2
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_location_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"location_name_field","text":"VRF-Station 25+00 '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"location_dialog_add"}'
   sleep 1
   ```

5. Add 2 contractors:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_contractors_tab"}'
   sleep 1
   # Contractor 1 (Prime)
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"contractor_name_field","text":"VRF-Midwest Excavating '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_type_prime"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_save_button"}'
   sleep 1
   # Contractor 2 (Sub)
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"contractor_name_field","text":"VRF-Allied Paving '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_type_sub"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_save_button"}'
   sleep 1
   ```

6. Add equipment to each contractor (expand card first):
   ```bash
   # Expand prime contractor card, add equipment
   # NOTE: contractor_card requires contractorId — tap card to expand
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"contractor_card_<contractorId>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_equipment_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"equipment_name_field","text":"VRF-CAT 320 Excavator '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"equipment_dialog_add"}'
   sleep 1
   # Second equipment
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_equipment_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"equipment_name_field","text":"VRF-Volvo A40G Hauler '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"equipment_dialog_add"}'
   sleep 1
   ```

7. Add pay item:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_payitems_tab"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_add_pay_item_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_source_manual"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"pay_item_number_field","text":"VRF-401"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"pay_item_description_field","text":"VRF-HMA Surface Course '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"pay_item_quantity_field","text":"500"}'
   # Unit is a dropdown, not text field
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_unit_dropdown"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_unit_ton"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"pay_item_dialog_save"}'
   sleep 1
   ```

8. Add 3 personnel types (via Settings):
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"settings_personnel_types_tile"}'
   sleep 1
   # Add 3 personnel types: Laborer, Operator, Foreman
   # For each type:
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"personnel_types_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"personnel_type_name_field","text":"VRF-Laborer '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"personnel_type_short_code_field","text":"LAB"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"add_personnel_type_confirm"}'
   sleep 1
   # Repeat for Operator (OPR) and Foreman (FOR) with same pattern
   ```

9. Assign inspector:
   ```bash
   # Navigate back to project edit → assignments tab
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_assignments_tab"}'
   sleep 1
   # Toggle inspector user assignment
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"assignment_tile_<INSPECTOR_USER_ID>"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_save_button"}'
   sleep 2
   ```

10. Sync admin → Supabase verify all 7 tables → capture all entity IDs into `ctx`.

11. Inspector sync (2 rounds) → verify projects, locations, contractors locally.

12. Create second project "VRF-Unassign Test {tag}":
    - Same flow as steps 1-3 but with different name
    - Assign inspector
    - Sync both devices
    - Capture `project2Id` into `ctx`

**Supabase Verify:** Query all 7 tables filtered by `projectId`. Capture IDs for:
- `ctx.locationIds` (2), `ctx.contractorIds` (2), `ctx.equipmentIds` (2)
- `ctx.bidItemIds` (1), `ctx.personnelTypeIds` (3), `ctx.assignmentId` (1)
- `ctx.project2Id` (1)

---

### S02: Daily Entry

**Tables:** daily_entries, entry_contractors, entry_equipment, entry_personnel_counts, entry_quantities
**Depends:** S01

**Admin (4948):**

1. Navigate to dashboard → add entry:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"add_entry_fab"}'
   sleep 1
   ```

2. Fill entry fields — select location, weather, temps, activities.

3. Add 2 entry contractors (toggle from project contractors).

4. Toggle equipment usage.

5. Add personnel counts.

6. Add quantity (select bid item, enter value).

7. Save as draft:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_wizard_save_draft"}'
   sleep 2
   ```

8. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `daily_entries`, `entry_contractors`, `entry_equipment`, `entry_personnel_counts`, `entry_quantities` by project_id.

**Capture:** `ctx.entryId`, `ctx.entryContractorIds`, `ctx.entryEquipmentIds`, `ctx.entryPersonnelCountIds`, `ctx.entryQuantityIds`

---

### S03: Photos

**Tables:** photos
**Depends:** S02

**Admin (4948):**

1. Inject photo directly (no camera needed):
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/inject-photo-direct \
     -d '{"base64Data":"<small-test-jpeg-base64>","filename":"VRF-test-photo-'"${RUN_TAG}"'.jpg","entryId":"<ctx.entryId>","projectId":"<ctx.projectId>"}'
   # NOTE: inject-photo-direct uses camelCase params (projectId, entryId, base64Data)
   # This is different from remove-from-device which uses snake_case (project_id)
   ```

2. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `photos?entry_id=eq.<entryId>`.

**Capture:** `ctx.photoIds`

**--- COMPACTION PAUSE ---**

---

### S04: Forms

**Tables:** inspector_forms, form_responses
**Depends:** S02

**Admin (4948):**

1. Navigate to entry → add form:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_add_form_button"}'
   sleep 1
   ```

2. Select 0582B form → fill header fields → save.

3. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `form_responses` by project_id.

**Capture:** `ctx.formResponseIds`

---

### S05: Todos

**Tables:** todo_items
**Depends:** S01

**Admin (4948):**

1. Navigate to toolbox → todos:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   # Toolbox is accessed via dashboard card, not bottom nav
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_toolbox_card"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"toolbox_todos_card"}'
   sleep 1
   ```

2. Create todo:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todos_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"todos_title_field","text":"VRF-Check rebar spacing '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todos_save_button"}'
   sleep 1
   ```

3. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `todo_items` by project_id.

**Capture:** `ctx.todoIds`

---

### S06: Calculator

**Tables:** calculation_history
**Depends:** S01

**Admin (4948):**

1. Navigate to toolbox → calculator:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   # Toolbox is accessed via dashboard card, not bottom nav
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_toolbox_card"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"toolbox_calculator_card"}'
   sleep 1
   ```

2. Select HMA tab → fill fields → calculate → save:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_tab"}'
   sleep 1
   # HMA inputs: area (sq ft), thickness (inches), density (lbs/cu ft)
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_area","text":"2400"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_thickness","text":"4"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_density","text":"145"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_calculate_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_save_button"}'
   sleep 1
   ```

3. Cross-device sync protocol (4-step).

**Supabase Verify:** Query `calculation_history` by project_id.

**Capture:** `ctx.calculationIds`

**--- COMPACTION PAUSE ---**

---

### S07: Update All

**Tables:** All updatable tables
**Depends:** S01-S06

**Admin (4948):**

Update each entity type created in S01-S06:

1. **Project name**: Edit → append " Phase 2" → save
2. **Location**: Edit location name → append " Ext" → save
3. **Contractor**: Edit contractor name → append " LLC" → save
4. **Equipment**: Edit equipment name → change model → save
5. **Bid item**: Edit description → append " (Modified)" → save
6. **Personnel type**: Edit name → save
7. **Daily entry**: Edit activities text → append " [updated]"
8. **Photo**: Edit description field
9. **Entry equipment**: Toggle equipment on/off
10. **Entry personnel count**: Increment count
11. **Form response**: Edit remarks field
12. **Entry quantity**: Update value
13. **Todo**: Update title → append " [done]"

After all updates:
- Sync admin
- Supabase verify: spot-check 3-4 key updates (project name, entry activities, todo title)
- Inspector sync x2 → verify updated project name locally

---

### S08: PDF Export

**Tables:** N/A (output artifact)
**Depends:** S07

**Admin (4948):**

1. Navigate to entry → export PDF:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_export_pdf_button"}'
   sleep 1
   ```

2. Enter filename → save → wait 5s for generation.

3. ADB pull the PDF (15s timeout):
   ```bash
   # Find the PDF on device, pull via adb
   # If timeout → FAIL S08, continue to S09
   ```

4. Verify with pdftk:
   ```bash
   pdftk <pulled.pdf> dump_data_fields_utf8
   # Check for expected field values
   ```

5. Export 0582B form PDF → verify similarly.

**If ADB times out:** Record FAIL for S08, continue to S09. PDF export is non-blocking.

---

### S09: Delete Cascade

**Tables:** All child tables of project 1
**Depends:** S07

**Admin (4948):**

1. Navigate to projects list:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"projects_nav_button"}'
   sleep 1
   ```

2. Two-step delete (soft-delete the project):
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"project_remove_<projectId>"}'
   sleep 1
   # Two-step delete: tap continue → type project name to confirm → tap delete forever
   # Step 1: tap continue/proceed button
   # Step 2: type project name in confirmation field, then tap delete forever button
   ```

3. Sync admin.

4. **Supabase verify cascade**: Query all 14 child tables — every record with `project_id=<projectId>` should have `is_deleted=true`. Project assignments should be hard-deleted.

   Tables to check: entry_personnel_counts, entry_equipment, entry_quantities, entry_contractors, photos, calculation_history, todo_items, form_responses, daily_entries, equipment, personnel_types, bid_items, contractors, locations, inspector_forms.

   Project assignments: query should return 0 rows (hard-deleted).

5. Inspector sync → check for `deletion_notification_banner` → verify project gone from local device:
   ```bash
   curl -s -X POST http://127.0.0.1:4949/driver/sync
   sleep 2
   curl -s -X POST http://127.0.0.1:4949/driver/sync
   sleep 2
   curl -s http://127.0.0.1:4949/driver/find?key=deletion_notification_banner
   # Verify project is no longer in local list
   ```

**--- COMPACTION PAUSE ---**

---

### S10: Unassignment + Cleanup

**Tables:** project_assignments, projects
**Depends:** S01

**Inspector (4949):**
1. Verify project2 exists locally:
   ```bash
   curl -s "http://127.0.0.1:4949/driver/local-record?table=projects&id=<ctx.project2Id>"
   ```

**Admin (4948):**
2. Edit project2 → assignments tab → toggle off inspector → save → sync:
   ```bash
   # Navigate to project2 edit → assignments tab
   # Toggle off inspector assignment
   # Save → sync
   ```

3. **Supabase verify**: project2 still exists, but assignment is hard-deleted:
   ```bash
   curl -s "${SUPABASE_URL}/rest/v1/projects?id=eq.<project2Id>&select=id,name" ...
   curl -s "${SUPABASE_URL}/rest/v1/project_assignments?project_id=eq.<project2Id>&select=id" ...
   # projects: 1 row. assignments: 0 rows.
   ```

**Inspector (4949):**
4. Sync x2 → verify project2 is removed from local device (unassigned = no longer visible):
   ```bash
   curl -s -X POST http://127.0.0.1:4949/driver/sync
   sleep 2
   curl -s -X POST http://127.0.0.1:4949/driver/sync
   sleep 2
   curl -s "http://127.0.0.1:4949/driver/local-record?table=projects&id=<ctx.project2Id>"
   # Should return not found / empty
   ```

**Admin (4948):**
5. Delete project2 → sync (cleanup):
   ```bash
   # Two-step delete project2, sync admin
   ```

**Post-Run Sweep:**
Query all 17 synced tables for any records with `VRF-` in name/description fields. Any remaining records = FAIL.

```bash
# Check projects
curl -s "${SUPABASE_URL}/rest/v1/projects?name=like.VRF-*&select=id,name" ...
# Check locations
curl -s "${SUPABASE_URL}/rest/v1/locations?name=like.VRF-*&select=id,name" ...
# Check contractors
curl -s "${SUPABASE_URL}/rest/v1/contractors?name=like.VRF-*&select=id,name" ...
# ... repeat for all tables with name/description fields
```

If any VRF records remain, record them in the report as FAIL.

---

## Report Protocol

Write `.claude/test_results/<run>/report.md` with these 6 sections:

### 1. Header
```markdown
# Sync Verification Report — <date> <time>
Platform: dual (android:4948 + windows:4949)
Run Tag: <RUN_TAG>
```

### 2. Results Table
```markdown
## Results
| Flow | Status | Duration | Notes |
|------|--------|----------|-------|
| S01  | PASS   | 45s      |       |
| S02  | PASS   | 30s      |       |
```

### 3. Supabase Verification Summary
```markdown
## Supabase Verification
| Table | Records Created | Records Verified | Cascade Deleted | Notes |
|-------|----------------|-----------------|-----------------|-------|
```

### 4. Cross-Device Sync Results
```markdown
## Cross-Device Sync
| Flow | Admin→Cloud | Cloud→Inspector | Latency | Notes |
|------|-------------|-----------------|---------|-------|
```

### 5. Log Anomalies
```markdown
## Log Anomalies
| Flow | Level | Category | Message | Timestamp |
|------|-------|----------|---------|-----------|
```

### 6. Bugs Found
```markdown
## Bugs Found
- **[BUG]** <description> — flow: S0X
```

### 7. Post-Run Sweep Results
```markdown
## Post-Run Sweep
| Table | VRF Records Found | Status |
|-------|-------------------|--------|
| projects | 0 | CLEAN |
```

### 8. Observations
```markdown
## Observations
- Sync averaged Xs per operation
- <any notable findings>
```

## Edge Cases

### ADB Flakiness
- If `adb` commands fail, retry once after 3s
- If S08 PDF pull fails, record FAIL for S08 only, continue to S09
- ADB is only needed for S08 (PDF export)

### Device Disconnects
- Before each flow, verify device is reachable: `curl -s http://127.0.0.1:<port>/driver/ready`
- If unreachable, retry once after 5s
- If still unreachable, **pause and ask user to reconnect** rather than failing silently
- Write checkpoint before pausing so progress is preserved

### Sync Errors
- If sync returns non-200, capture response body and error logs
- Retry sync once after 5s
- If still failing, FAIL the current flow

### Already Logged In
- Both devices should already be logged in before starting S01
- If a device shows the login screen, log in with the appropriate credentials from `.claude/test-credentials.secret`

### Context Exhaustion
- The compaction pauses after S03, S06, S09 are designed to prevent this
- If context is exhausted mid-flow, the checkpoint has all IDs needed to resume
- On resume, read checkpoint.json and restore all `ctx` values before continuing
```

**Verification:** Confirm the file exists and is well-formed markdown.

---

## Verification

No automated verification is needed for this plan:
- Phase 1: File deletions — verify files are gone with `ls`
- Phase 2: `node tools/debug-server/run-tests.js --help` — confirm new help text
- Phase 3-4: Visual inspection of markdown files
- No Dart code changes, no `flutter test` needed
