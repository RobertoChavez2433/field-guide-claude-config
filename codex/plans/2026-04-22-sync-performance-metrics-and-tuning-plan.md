## Sync Performance Metrics And Tuning Plan

Date: 2026-04-22
Status: complete for the live push-pull performance lane; broader UI whole-cycle follow-up deferred
Owner: Codex
Related:

- `.codex/plans/2026-04-18-sync-engine-external-hardening-todo.md`
- `lib/features/sync/engine/sync_engine.dart`
- `lib/features/sync/engine/push_handler.dart`
- `lib/features/sync/engine/pull_handler.dart`
- `lib/features/sync/engine/supabase_sync.dart`
- `lib/features/sync/application/sync_query_service.dart`

### Goal

Build a real measurement and tuning lane for sync so we can answer three
questions with evidence instead of intuition:

1. Where does the current 2-3 second full sync time go?
2. Which parts of that time are acceptable network/setup cost versus avoidable
   engine overhead?
3. Which low-risk changes can move small-record syncs closer to sub-second
   behavior without weakening correctness or diagnostics?

### Closure Summary

- The live S21 push-plus-pull acceptance target for the medium full UI lane is
  met on live Supabase:
  - accepted proof:
    `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration12/summary.json`
  - accepted result: `1583ms` push + `1098ms` pull = `2681ms` combined
- The broader observed dashboard-driven full-sync cycle remains above `3000ms`
  and is now a separate non-engine follow-up lane rather than an open blocker
  on this plan.

### Payload Matrix

We need timing by payload size, not just one generic "full sync" number. The
measurement set should cover at least these tiers on live Supabase:

- tiny payload
  - no-op sync or near-empty delta
  - a few row changes across 1-2 tables
- small payload
  - realistic everyday field use
  - tens of changed rows across the common tables
- medium payload
  - a fuller project delta with cross-table fan-out
  - low hundreds of rows when related records are included
- file-backed payload
  - at least one photo/signature/document-backed sync shape kept separate from
    pure row sync timing

Each timing artifact should label:

- payload tier
- approximate changed-row count
- tables touched
- whether file transfer or storage cleanup was involved
- full sync or quick sync mode
- device and session context

### Current Signals

- The app already records total sync duration in `SyncRunLifecycle.finish()`,
  but it does not break the run into push, pull, maintenance, checkpoint, or
  per-table/page timing.
- Full sync currently always includes:
  - push batches
  - storage cleanup
  - full pull
  - housekeeping
  - optional repair pull if integrity clears cursors
  - freshness proof before the run is marked successful
- Pull paging already uses `(updated_at, id)` ordering, but we still need to
  measure how many page/table round trips a "small" sync is paying for.

### 2026-04-22 Audit And Iteration Update

- The first optimization wave was the right move: batched write-checkpoint
  proof reads removed checkpoint verification as the dominant medium-payload
  cost.
- The follow-up audit showed the remaining 30s to 40s S21 runs were dominated
  by push, not checkpoint proof or auth wait.
- Code audit confirmed two expensive per-row remote calls in the hot push path:
  - `LwwChecker.shouldSkipPush()` fetched `updated_at` from Supabase one record
    at a time for non-file upserts.
  - `RpcSyncHintRemoteEmitter.emit()` sent a separate `emit_sync_hint` RPC for
    every pushed row even though sync hints are coarse invalidation signals.
- External sync-engine references matched that diagnosis:
  - Replicache batches pushes and uses contentless realtime pokes instead of
    per-record notifications.
  - PowerSync emphasizes partial sync, delta/history-backed checkpoints, and
    coarse upload/write-checkpoint coordination rather than row-by-row hinting.
  - AWS AppSync and Couchbase both treat delta/base sync selection as a
    checkpointed server concern, not something the client solves with repeated
    small polling calls.
- Implemented second optimization wave:
  - buffered/coalesced sync-hint emission per table/project scope instead of
    per-row RPCs
  - batched server `updated_at` prefetch for non-file, non-natural-key LWW
    checks
- Latest live S21 results after that wave:
  - `medium-row-full`: `30295ms -> 15796ms`; push `26471ms -> 12179ms`
  - `medium-row-quick`: `30495ms -> 14302ms`; push `26848ms -> 12130ms`
  - `tiny-noop-full`: `3673ms -> 3584ms`; pull still `2902ms -> 2849ms` across
    `22` pull pages
- Current verdict:
  - for large row-backed syncs, the current path was correct and materially
    improved performance
  - for no-op/full syncs, the next best target is pull fan-out reduction or
    scoped full-pull narrowing, not more push/checkpoint work
- Iteration 4 confirmed the next push-side step as well:
  - guarded bulk upsert for eligible simple-table adapters cut
    `medium-row-full` from `16412ms` to `5248ms`
  - `medium-row-quick` fell from `13858ms` to `5096ms`
  - the hot row-backed tables now push in sub-second table windows on S21
  - the next medium-path audit target is local push overhead outside the
    per-table remote execution window, especially repeated local reads and
    per-row queue acknowledgement
- Iteration 5 confirmed that the remaining easy local wins were worth taking:
  - batching local queue acknowledgement plus planner/preparation row preloads
    cut `medium-row-full` again from `5248ms` to `4663ms`
  - `medium-row-quick` fell from `5096ms` to `4179ms`
  - warm `tiny-noop-full` reached `1406ms` on S21 when the device stayed on
    the narrower non-exhaustive path
- the next likely gains are no longer small batching tweaks; they are either
  broader table-level preparation collapse or further stale-device
  exhaustive-pull narrowing
- Iteration 6 added shared push-planning caches plus overlapped per-table LWW
  priming and also fixed the matrix summary markdown writer:
  - `medium-row-full`: `4027ms -> 3818ms`; push `1997ms -> 1792ms`
  - `medium-row-quick`: `3775ms -> 3166ms`; push `2088ms -> 1417ms`
  - the live artifact contract is more reliable now because the matrix no
    longer dies when markdown rendering sees a non-string summary value
- Iteration 7 removed the final duplicate local row reads after planning and
  added scoped-full direct-table opt-out support:
  - latest accepted artifact:
    `tools/testing/test-results/2026-04-22/live-sync-performance-tuned-S21-20260422-101550/summary.json`
  - `medium-row-full`: push `1722ms` + pull `1259ms` = `2981ms` combined
  - `medium-row-quick`: `2964ms` observed; push `1300ms`, pull `903ms`
  - the requested warm S21 medium full push-plus-pull target is now met, but
    the broader observed full-sync duration and the exhaustive no-op full path
    still need work

### Non-Negotiables

- Use real sync behavior, real auth, real backend state, and real SQLite
  triggers.
- Use the live Supabase environment for measurement and acceptance. Do not use
  the local harness as the main evidence source for this performance lane.
- Do not add test-only hooks or bypasses to make timing look good.
- Keep the diagnostics honest: faster sync is not useful if we lose
  visibility into blocked queues, reconciliation, or checkpoint proof.
- Do not optimize the wrong surface. We need to separate:
  - engine work
  - network latency
  - startup/auth context wait
  - dashboard query/render time

### Phase 1: Establish A Baseline

- [ ] Record a reproducible baseline for the payload matrix, not just one sync
  shape.
- [ ] For each payload tier, capture at minimum:
  - full sync timing
  - quick sync timing when that mode is valid for the scenario
  - pushed/pulled row counts
  - tables touched
  - whether file-backed work was involved
- [ ] Start with these live Supabase baseline scenarios:
  - tiny no-op or near-no-op sync
  - tiny delta sync
  - small pure-row sync
  - medium pure-row sync
  - file-backed sync as a separate lane
- [ ] Run the baseline only against live Supabase with real sessions.
- [ ] Start with one real-device measurement lane on S21 using the lighter
  `flutter run` path.
- [ ] Add one secondary live lane after S21 is stable so we can compare device
  classes without mixing too many variables.
  - preferred second lane: tablet emulator against the same live backend
- [ ] Save artifacts under `tools/testing/test-results/<date>/` with:
  - run shape
  - payload tier
  - approximate row volume
  - touched tables
  - file-backed or row-only classification
  - device context
  - total duration
  - pushed/pulled counts
  - pending/blocked counts before and after
- [ ] Define the first performance budget in writing instead of guessing:
  - provisional target: small warm sync under `1000ms`
  - provisional target: warm quick sync under `500ms`
  - do not lock stricter numbers until the first baseline is captured

### Phase 2: Add Phase-Level Instrumentation

- [ ] Add structured sync timing data instead of only a single total duration.
- [ ] Extend the recent-run diagnostics surface so one completed run can report:
  - total duration
  - push duration
  - pull duration
  - maintenance duration
  - write-checkpoint verification duration
  - auth/context-resolution wait duration
  - per-table pull timing and row counts
  - per-table push timing and row counts
  - pull page count and average page time
- [ ] Thread that timing through existing production diagnostics surfaces rather
  than inventing a separate debug-only store.
  - likely owners: `SyncRunLifecycle`, `SyncEvent`, `RecentRunSummary`,
    `SyncDiagnosticsSnapshot`, and `SyncQueryService`
- [ ] Keep the payload compact enough for dashboards, debug logs, and driver
  snapshots.
- [ ] Add tests that lock the timing contract shape so future refactors do not
  silently remove the fields.

### Phase 3: Identify The Expensive Path

- [ ] Use the new timing breakdown to identify whether the current cost is
  dominated by:
  - auth/context resolution
  - push queue enumeration
  - per-record push routing
  - storage cleanup
  - pull table fan-out
  - pull pagination
  - housekeeping or integrity work
  - write-checkpoint verification
  - diagnostics refresh after sync
- [ ] Compare the timing curve across payload tiers so we can tell whether the
  cost is:
  - mostly fixed overhead
  - roughly linear with row count
  - disproportionately bad for file-backed or fan-out-heavy tables
- [ ] Capture at least one example where a "small" sync still touches many
  tables, so we can see whether table fan-out is the real tax.
- [ ] Separate "no-op sync" cost from "actual delta" cost. If a no-op full sync
  is still expensive, the issue is orchestration overhead rather than data size.
- [ ] Produce a short hotspot summary before changing behavior.

### Phase 4: Low-Risk Optimizations First

- [ ] Audit full-sync work that runs unconditionally and measure whether it can
  be skipped, deferred, or narrowed for small runs.
  - storage cleanup
  - housekeeping/integrity passes
  - repair pull retry path
  - freshness proof
- [ ] Check whether pull work can stop earlier when no tables have changes
  beyond the current checkpoint.
- [ ] Check whether push work is doing avoidable repeated queries or record
  fetches per change.
- [ ] Inspect dashboard diagnostics queries separately from engine time so we do
  not blame the sync engine for post-run UI refresh cost.
- [ ] Tune for the common small-record path first. Do not trade away correctness
  on file-backed or high-volume lanes just to speed up no-op runs.

### Phase 5: Medium-Risk Tuning Candidates

- [ ] If the data shows pull table fan-out is the main cost, evaluate a more
  selective scoped pull plan for full sync when the user/project scope is known
  and stable.
- [ ] If page round trips are the main cost, evaluate larger page sizes or
  table-specific paging rules for small-table adapters.
- [ ] If write-checkpoint proof is a major cost, evaluate whether its reads can
  be scoped to touched tables instead of all synced tables.
- [ ] If maintenance is a major cost, evaluate moving heavy integrity work to a
  less frequent maintenance lane instead of every small full sync.
- [ ] If auth/context resolution is a major cost, evaluate caching or warming
  the sync context path before the user manually requests a sync.

### Phase 6: Regression And Acceptance Gates

- [ ] Add repeatable live timing runs for S21 after each meaningful
  optimization wave.
- [ ] Add at least one secondary live-device or live-emulator comparison run
  once the S21 lane is stable.
- [ ] Keep correctness gates in place while tuning:
  - no blocked rows introduced
  - no queue drain regressions
  - no stale role/project visibility
  - no file-sync or checkpoint regressions
- [ ] Track the before/after delta for each optimization so we know which
  changes actually moved the needle.

### Deliverables

- [ ] Structured sync timing model wired into diagnostics and events
- [ ] Baseline live Supabase performance artifacts for S21 and one secondary
  live lane
- [ ] Payload-tier timing table showing how duration changes with row volume and
  file-backed work
- [ ] One hotspot summary with ranked bottlenecks
- [ ] A first optimization pass with measured before/after improvement
- [ ] Updated timing tests guarding the new contract

### Expected First Implementation Slice

1. Add phase timing capture to the sync run lifecycle and diagnostics model.
2. Define and seed the first live Supabase payload tiers for S21 timing.
3. Run one S21 measurement pass across those payload tiers.
4. Rank the hotspots and the payload scaling curve.
5. Apply the safest optimization that the measurements support.
6. Re-run the same measurements and compare.

### Recent Progress

- Iteration 8 completed the UI-cycle audit and corrected the measurement path:
  - `/driver/sync-status` now reports UI sync state separately from the shared
    sync gate
  - `tools/measure-device-sync.ps1` now measures the UI state with a tighter
    `100ms` poll interval
  - `SyncProvider` no longer extends `isSyncing` through the post-sync provider
    refresh callback
  - live proof: `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration8/summary.json`
  - result: `medium-row-full` still measured `5563ms`, so the remaining gap is
    not just UI timing semantics

- Iteration 9 reduced create-heavy push overhead by skipping LWW timestamp
  checks for insert operations while keeping them for updates:
  - live proof: `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration9/summary.json`
  - result: `medium-row-full` improved to `4798ms`
  - push improved `2893ms -> 2550ms`
  - pull improved `1751ms -> 1474ms`

- Iteration 10 hardened the live matrix summary writer and confirmed that the
  larger pull page size improved the UI-driven live S21 run:
  - live proof: `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration10c/summary.json`
  - result: `medium-row-full` measured `4634ms`
  - push measured `2677ms`
  - pull improved to `1188ms`
  - `summary.json` and `summary.md` now write reliably from the same run

- Iteration 11 batched local server-timestamp write-back after bulk upsert:
  - live proof: `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration11/summary.json`
  - result: `medium-row-full` measured `3885ms`
  - push improved to `1899ms`
  - pull measured `1268ms`
  - combined push-plus-pull improved to `3167ms`

- Iteration 12 reused the already-resolved project scope when emitting sync
  hints on bulk and single-row push paths:
  - live proof: `tools/testing/test-results/2026-04-22/live-sync-performance-ui-cycle-S21-20260422-iteration12/summary.json`
  - result: `medium-row-full` measured `3364ms`
  - push improved to `1583ms`
  - pull improved to `1098ms`
  - combined push-plus-pull reached `2681ms`

- Current accepted read:
  - the live S21 dashboard-driven medium full path is now back under the
    requested sub-`3000ms` combined push-plus-pull target on live Supabase
  - the broader observed UI-driven full-sync duration is still above `3000ms`,
    so the next lane, if needed, is non-engine whole-cycle overhead rather than
    the core push-plus-pull engine path
  - checkpoint proof and maintenance are no longer the primary bottlenecks
